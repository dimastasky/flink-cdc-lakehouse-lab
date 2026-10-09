package lab;
import org.junit.jupiter.api.Test;
import java.util.Random;
import java.math.BigDecimal;
import static org.junit.jupiter.api.Assertions.*;
class GeneratorTest {
 @Test void moneyIsExactAndReproducible(){Random a=new Random(42),b=new Random(42);for(int i=0;i<1000;i++){BigDecimal x=WorkloadGenerator.amount(a);assertEquals(x,WorkloadGenerator.amount(b));assertEquals(2,x.scale());assertTrue(x.signum()>0);}}
 @Test void transitionsAreFinite(){assertEquals("PENDING",WorkloadGenerator.nextStatus("CREATED"));assertEquals("COMPLETED",WorkloadGenerator.nextStatus("PENDING"));assertEquals("REFUNDED",WorkloadGenerator.nextStatus("COMPLETED"));assertEquals("FAILED",WorkloadGenerator.nextStatus("FAILED"));}
 @Test void validatesBounds(){assertThrows(IllegalArgumentException.class,()->GeneratorConfig.parse(new String[]{"--rate","0"}));assertThrows(IllegalArgumentException.class,()->GeneratorConfig.parse(new String[]{"--mode","forever"}));assertTrue(GeneratorConfig.parse(new String[]{"--dry-run"}).dryRun());}
}
