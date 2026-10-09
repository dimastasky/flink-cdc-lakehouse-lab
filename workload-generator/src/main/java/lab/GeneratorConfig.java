package lab;

public record GeneratorConfig(String mode, long seed, int rate, int duration, int batchSize, boolean dryRun) {
    public static GeneratorConfig parse(String[] args) {
        String mode="continuous"; long seed=42; int rate=20,duration=120,batch=20; boolean dry=false;
        for(int i=0;i<args.length;i++) {
            switch(args[i]) {
                case "--mode" -> mode=args[++i];
                case "--seed" -> seed=Long.parseLong(args[++i]);
                case "--rate" -> rate=Integer.parseInt(args[++i]);
                case "--duration" -> duration=Integer.parseInt(args[++i]);
                case "--batch-size" -> batch=Integer.parseInt(args[++i]);
                case "--dry-run" -> dry=true;
                default -> throw new IllegalArgumentException("Unknown option: "+args[i]);
            }
        }
        if(!java.util.Set.of("seed","finite","continuous").contains(mode) || rate<1 || rate>10000 || duration<1 || duration>86400 || batch<1 || batch>1000)
            throw new IllegalArgumentException("Invalid mode/rate/duration/batch-size");
        return new GeneratorConfig(mode,seed,rate,duration,batch,dry);
    }
}
