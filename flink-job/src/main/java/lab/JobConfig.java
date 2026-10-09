package lab;

import java.util.Map;

public record JobConfig(int parallelism, long interval, long timeout, long pause, int restartAttempts) {
    public static JobConfig from(Map<String,String> env) {
        var c = new JobConfig(integer(env,"PARALLELISM",1), integer(env,"CHECKPOINT_INTERVAL_MS",10000),
            integer(env,"CHECKPOINT_TIMEOUT_MS",120000),integer(env,"CHECKPOINT_MIN_PAUSE_MS",1000),integer(env,"RESTART_ATTEMPTS",10));
        if(c.parallelism < 1 || c.parallelism > integer(env,"TASK_SLOTS",4) || c.interval < 1000 || c.timeout <= c.interval || c.pause < 0 || c.restartAttempts < 1)
            throw new IllegalArgumentException("Invalid parallelism/checkpoint/restart configuration");
        return c;
    }
    private static int integer(Map<String,String> e,String k,int d) {return Integer.parseInt(e.getOrDefault(k,Integer.toString(d)));}
    public static String required(Map<String,String> e,String key) {
        String v=e.get(key); if(v==null || v.isBlank()) throw new IllegalArgumentException("Missing "+key); return v;
    }
    public static String sqlLiteral(String value) {return value.replace("'","''");}
}
