package vn.lacvietnode.lich;

import android.os.Bundle;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(LvCalendarPlugin.class);
        registerPlugin(LvSystemPlugin.class);
        super.onCreate(savedInstanceState);
    }
}
