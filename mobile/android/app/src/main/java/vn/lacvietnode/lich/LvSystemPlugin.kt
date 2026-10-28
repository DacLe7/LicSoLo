package vn.lacvietnode.lich

import android.content.ActivityNotFoundException
import android.content.ComponentName
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.provider.Settings
import com.getcapacitor.JSObject
import com.getcapacitor.Plugin
import com.getcapacitor.PluginCall
import com.getcapacitor.PluginMethod
import com.getcapacitor.annotation.CapacitorPlugin

/** Mở các trang cài đặt hệ thống mà người dùng phải tự bật (quyền, tự khởi động, pin, báo thức chính xác). */
@CapacitorPlugin(name = "LvSystem")
class LvSystemPlugin : Plugin() {

    private fun launch(i: Intent): Boolean = try {
        i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        context.startActivity(i)
        true
    } catch (e: ActivityNotFoundException) {
        false
    } catch (e: SecurityException) {
        false
    }

    private fun appDetails() = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.parse("package:" + context.packageName))

    @PluginMethod
    fun openAppSettings(call: PluginCall) {
        call.resolve(JSObject().put("opened", launch(appDetails())))
    }

    /** HyperOS/MIUI: trang "Tự khởi động". Không có thì mở thông tin ứng dụng. */
    @PluginMethod
    fun openAutostart(call: PluginCall) {
        val miui = Intent().setComponent(
            ComponentName("com.miui.securitycenter", "com.miui.permcenter.autostart.AutoStartManagementActivity")
        )
        val ok = launch(miui)
        call.resolve(JSObject().put("opened", ok || launch(appDetails())).put("direct", ok))
    }

    @PluginMethod
    fun openBatterySettings(call: PluginCall) {
        val ok = launch(Intent(Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS))
        call.resolve(JSObject().put("opened", ok || launch(appDetails())))
    }

    @PluginMethod
    fun openExactAlarmSettings(call: PluginCall) {
        val ok = Build.VERSION.SDK_INT >= 31 &&
            launch(Intent(Settings.ACTION_REQUEST_SCHEDULE_EXACT_ALARM, Uri.parse("package:" + context.packageName)))
        call.resolve(JSObject().put("opened", ok || launch(appDetails())))
    }
}
