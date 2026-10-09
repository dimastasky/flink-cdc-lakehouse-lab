package lab;

import java.math.BigDecimal;
import java.sql.*;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.Random;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;

/** Intentionally plain JDBC; synthetic payments are not a banking ledger. */
public final class WorkloadGenerator {
    private static final AtomicBoolean RUNNING=new AtomicBoolean(true);
    private static final CountDownLatch FINISHED=new CountDownLatch(1);
    public static BigDecimal amount(Random r) {return BigDecimal.valueOf(1+r.nextInt(100000),2);}
    public static String nextStatus(String status) {
        return switch(status) {case "CREATED" -> "PENDING"; case "PENDING" -> "COMPLETED"; case "COMPLETED" -> "REFUNDED"; default -> status;};
    }
    public static void main(String[] args) throws Exception {
        var cfg=GeneratorConfig.parse(args);
        System.out.printf("{\"event\":\"start\",\"mode\":\"%s\",\"seed\":%d,\"rate\":%d,\"dryRun\":%s}%n",cfg.mode(),cfg.seed(),cfg.rate(),cfg.dryRun());
        if(cfg.dryRun()) {var r=new Random(cfg.seed());for(int i=0;i<3;i++)System.out.println("sample amount="+amount(r));return;}
        Runtime.getRuntime().addShutdownHook(new Thread(()->{RUNNING.set(false);try{FINISHED.await(15,TimeUnit.SECONDS);}catch(InterruptedException e){Thread.currentThread().interrupt();}}));
        try(var db=DriverManager.getConnection(System.getenv().getOrDefault("JDBC_URL","jdbc:postgresql://postgres-oltp:5432/payments?ApplicationName=lab-generator&connectTimeout=10&socketTimeout=20"),"lab_app",System.getenv("APP_PASSWORD"))) {
            db.setAutoCommit(false);
            try {
                switch(cfg.mode()) {case "seed" -> seed(db,cfg);case "finite" -> finite(db,cfg);case "continuous" -> continuous(db,cfg);default -> throw new AssertionError();}
            } catch(Exception e){db.rollback();throw e;}
        } finally {FINISHED.countDown();}
        System.out.println("{\"event\":\"finished\",\"transactionsClosed\":true}");
    }
    private static void seed(Connection db,GeneratorConfig cfg) throws SQLException {
        execute(db,"SELECT pg_advisory_xact_lock(712031)");
        try(var s=db.createStatement();var rs=s.executeQuery("SELECT seed FROM lab_seed")) {
            if(rs.next()){if(rs.getLong(1)!=cfg.seed())throw new IllegalStateException("Dataset already seeded with another seed");db.commit();System.out.println("{\"event\":\"seed_already_present\"}");return;}
        }
        try(var s=db.createStatement();var rs=s.executeQuery("SELECT (SELECT count(*) FROM customers)+(SELECT count(*) FROM accounts)+(SELECT count(*) FROM payments)")){
            rs.next();if(rs.getLong(1)!=0)throw new IllegalStateException("Refuse seed into an unmarked nonempty dataset");
        }
        var r=new Random(cfg.seed());
        for(int i=1;i<=100;i++) update(db,"INSERT INTO customers(customer_id,full_name,country_code,status,created_at,updated_at) VALUES (?, ?, ?, 'ACTIVE', ?, ?)",i,"Synthetic Customer "+i,i%5==0?null:"US",time(i),time(i));
        for(int i=1;i<=200;i++) update(db,"INSERT INTO accounts(account_id,customer_id,currency,status,created_at,updated_at) VALUES (?, ?, ?, 'ACTIVE', ?, ?)",i,(i-1)%100+1,currency(i),time(i),time(i));
        try(var p=db.prepareStatement("INSERT INTO payments(payment_id,account_id,amount,currency,status,event_time,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)")) {
            for(int i=1;i<=10000;i++) {
                int account=(i-1)%200+1;
                Object[] row={i,account,amount(r),currency(account),i%2==0?"COMPLETED":"CREATED",time(i),time(i),time(i)};
                bind(p,row);p.addBatch();if(i%cfg.batchSize()==0)p.executeBatch();
            }
            p.executeBatch();
        }
        execute(db,"SELECT setval('customer_ids',100),setval('account_ids',200),setval('payment_ids',10000)");
        update(db,"INSERT INTO lab_seed(seed) VALUES (?)",cfg.seed()); db.commit();
        System.out.println("{\"event\":\"seeded\",\"customers\":100,\"accounts\":200,\"payments\":10000}");
    }
    private static String currency(int account) {return switch(account%3){case 0->"USD";case 1->"EUR";default->"RUB";};}
    private static OffsetDateTime time(long offset){return Instant.parse("2026-01-01T00:00:00.123Z").plusMillis(offset).atOffset(ZoneOffset.UTC);}
    private static void finite(Connection db,GeneratorConfig cfg) throws SQLException {
        long customer=id(db,"INSERT INTO customers(full_name,country_code,status) VALUES ('Synthetic finite',NULL,'ACTIVE') RETURNING customer_id");
        long account=id(db,"INSERT INTO accounts(customer_id,currency,status) VALUES (?,'USD','ACTIVE') RETURNING account_id",customer);
        long payment=id(db,"INSERT INTO payments(account_id,amount,currency,status,event_time) VALUES (?,?,'USD','CREATED',?) RETURNING payment_id",account,amount(new Random(cfg.seed())),time(42));
        long deleted=id(db,"INSERT INTO payments(account_id,amount,currency,status,event_time) VALUES (?,0.01,'USD','CREATED',?) RETURNING payment_id",account,time(43));
        db.commit();
        update(db,"UPDATE payments SET status='PENDING' WHERE payment_id=?",payment);db.commit();
        update(db,"UPDATE payments SET status='COMPLETED' WHERE payment_id=?",payment);
        update(db,"UPDATE customers SET full_name='Synthetic finite updated',country_code='US' WHERE customer_id=?",customer);
        update(db,"UPDATE accounts SET status='CLOSED' WHERE account_id=?",account);db.commit();
        update(db,"UPDATE payments SET amount=999.99 WHERE payment_id=?",payment);db.rollback();
        // Amount correction is a separate committed transaction, not an implicit status side effect.
        update(db,"UPDATE payments SET amount=42.37 WHERE payment_id=?",payment);db.commit();
        update(db,"DELETE FROM payments WHERE payment_id=?",deleted);db.commit();
        System.out.printf("{\"event\":\"finite_done\",\"paymentId\":%d,\"deletedId\":%d}%n",payment,deleted);
    }
    private static void continuous(Connection db,GeneratorConfig cfg) throws Exception {
        Random random=new Random(cfg.seed());long start=System.nanoTime(),end=start+TimeUnit.SECONDS.toNanos(cfg.duration());long operations=0;
        while(RUNNING.get() && System.nanoTime()<end){
            int count=0;
            while(count<cfg.batchSize() && RUNNING.get() && System.nanoTime()<end){
                long payment=1+random.nextInt(10000);
                update(db,"UPDATE payments SET amount=amount+0.01 WHERE payment_id=?",payment);
                count++;operations++;
                long due=start+operations*1_000_000_000L/cfg.rate();
                while(RUNNING.get() && System.nanoTime()<Math.min(due,end))
                    TimeUnit.NANOSECONDS.sleep(Math.min(50_000_000L,Math.min(due,end)-System.nanoTime()));
            }
            db.commit();
        }
        System.out.printf("{\"event\":\"load_done\",\"operations\":%d}%n",operations);
    }
    private static void bind(PreparedStatement p,Object... values)throws SQLException {for(int i=0;i<values.length;i++)p.setObject(i+1,values[i]);}
    private static int update(Connection db,String sql,Object... args)throws SQLException {try(var s=db.prepareStatement(sql)){bind(s,args);return s.executeUpdate();}}
    private static long id(Connection db,String sql,Object... args)throws SQLException {try(var s=db.prepareStatement(sql)){bind(s,args);try(var r=s.executeQuery()){r.next();return r.getLong(1);}}}
    private static void execute(Connection db,String sql)throws SQLException {try(var s=db.createStatement()){s.execute(sql);}}
}
