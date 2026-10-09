package lab;
import org.junit.jupiter.api.Test;
import java.util.Map;
import static org.junit.jupiter.api.Assertions.*;
class JobConfigTest {
 @Test void boundedConfig(){assertEquals(10000,JobConfig.from(Map.of()).interval());assertThrows(IllegalArgumentException.class,()->JobConfig.from(Map.of("PARALLELISM","5")));assertThrows(IllegalArgumentException.class,()->JobConfig.from(Map.of("CHECKPOINT_TIMEOUT_MS","100")));}
 @Test void secretsAreRequiredAndEscaped(){assertThrows(IllegalArgumentException.class,()->JobConfig.required(Map.of(),"secret"));assertEquals("a''b",JobConfig.sqlLiteral("a'b"));}
}
