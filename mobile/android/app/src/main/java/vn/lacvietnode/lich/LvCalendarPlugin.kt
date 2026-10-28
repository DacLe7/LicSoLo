package vn.lacvietnode.lich

import android.Manifest
import android.content.ContentProviderOperation
import android.content.ContentUris
import android.content.ContentValues
import android.net.Uri
import android.provider.CalendarContract
import android.provider.CalendarContract.Calendars
import android.provider.CalendarContract.Events
import com.getcapacitor.JSArray
import com.getcapacitor.JSObject
import com.getcapacitor.PermissionState
import com.getcapacitor.Plugin
import com.getcapacitor.PluginCall
import com.getcapacitor.PluginMethod
import com.getcapacitor.annotation.CapacitorPlugin
import com.getcapacitor.annotation.Permission
import org.json.JSONObject
import java.util.TimeZone

/**
 * Lịch riêng "Trợ lý thời gian" trong lịch hệ thống. Đồng bộ một chiều: lịch để chỉ đọc (CAL_ACCESS_READ),
 * mọi ghi đi qua URI CALLER_IS_SYNCADAPTER. Mỗi sự kiện mang ref trong _SYNC_ID và mã băm nội dung trong SYNC_DATA1.
 * Plugin cố ý "ngu": mọi phép tính giờ làm ở TypeScript (src/sync.ts), ở đây chỉ ghi lại.
 */
@CapacitorPlugin(
    name = "LvCalendar",
    permissions = [Permission(strings = [Manifest.permission.READ_CALENDAR, Manifest.permission.WRITE_CALENDAR], alias = "calendar")]
)
class LvCalendarPlugin : Plugin() {

    private val account = "LicSoLo"
    private val accountType = CalendarContract.ACCOUNT_TYPE_LOCAL
    private val batchSize = 400

    private fun granted() = getPermissionState("calendar") == PermissionState.GRANTED

    private fun asSyncAdapter(uri: Uri): Uri = uri.buildUpon()
        .appendQueryParameter(CalendarContract.CALLER_IS_SYNCADAPTER, "true")
        .appendQueryParameter(Calendars.ACCOUNT_NAME, account)
        .appendQueryParameter(Calendars.ACCOUNT_TYPE, accountType)
        .build()

    private fun findCalendarId(): Long? {
        context.contentResolver.query(
            Calendars.CONTENT_URI, arrayOf(Calendars._ID),
            "${Calendars.ACCOUNT_NAME}=? AND ${Calendars.ACCOUNT_TYPE}=?", arrayOf(account, accountType), null
        )?.use { c -> if (c.moveToFirst()) return c.getLong(0) }
        return null
    }

    private fun ensureCalendarId(): Long {
        findCalendarId()?.let { return it }
        val v = ContentValues().apply {
            put(Calendars.ACCOUNT_NAME, account)
            put(Calendars.ACCOUNT_TYPE, accountType)
            put(Calendars.NAME, "lichsolo")
            put(Calendars.CALENDAR_DISPLAY_NAME, "Trợ lý thời gian")
            put(Calendars.CALENDAR_COLOR, 0xFFC2410C.toInt())
            put(Calendars.CALENDAR_ACCESS_LEVEL, Calendars.CAL_ACCESS_READ)
            put(Calendars.OWNER_ACCOUNT, account)
            put(Calendars.VISIBLE, 1)
            put(Calendars.SYNC_EVENTS, 1)
            put(Calendars.CALENDAR_TIME_ZONE, TimeZone.getDefault().id)
        }
        val uri = context.contentResolver.insert(asSyncAdapter(Calendars.CONTENT_URI), v)
            ?: throw IllegalStateException("Không tạo được lịch")
        return ContentUris.parseId(uri)
    }

    private fun eventValues(o: JSONObject, calendarId: Long?): ContentValues = ContentValues().apply {
        if (calendarId != null) put(Events.CALENDAR_ID, calendarId)
        put(Events.TITLE, o.getString("title"))
        put(Events.DESCRIPTION, o.optString("notes", ""))
        put(Events.DTSTART, o.getLong("startMs"))
        put(Events.DTEND, o.getLong("endMs"))
        put(Events.EVENT_TIMEZONE, o.getString("tz"))
        put(Events.ALL_DAY, if (o.optBoolean("allDay")) 1 else 0)
        put(Events.HAS_ALARM, 0) // app tự nhắc bằng thông báo của mình; gắn thêm thì bị nhắc hai lần
        put(Events._SYNC_ID, o.getString("ref"))
        put(Events.SYNC_DATA1, o.getString("hash"))
    }

    private fun eventUri(id: Long) = asSyncAdapter(ContentUris.withAppendedId(Events.CONTENT_URI, id))

    @PluginMethod
    fun ensureCalendar(call: PluginCall) {
        if (!granted()) return call.reject("Chưa cấp quyền lịch", "PERMISSION")
        try {
            call.resolve(JSObject().put("calendarId", ensureCalendarId()))
        } catch (e: Exception) {
            call.reject(e.message ?: "Lỗi lịch", e)
        }
    }

    @PluginMethod
    fun listManaged(call: PluginCall) {
        if (!granted()) return call.reject("Chưa cấp quyền lịch", "PERMISSION")
        try {
            val out = JSArray()
            val id = findCalendarId()
            if (id != null) {
                context.contentResolver.query(
                    Events.CONTENT_URI, arrayOf(Events._ID, Events._SYNC_ID, Events.SYNC_DATA1),
                    "${Events.CALENDAR_ID}=? AND ${Events.DELETED}=0", arrayOf(id.toString()), null
                )?.use { c ->
                    while (c.moveToNext()) {
                        out.put(JSObject().put("eventId", c.getLong(0)).put("ref", c.getString(1) ?: "").put("hash", c.getString(2) ?: ""))
                    }
                }
            }
            call.resolve(JSObject().put("items", out))
        } catch (e: Exception) {
            call.reject(e.message ?: "Lỗi lịch", e)
        }
    }

    @PluginMethod
    fun applyDiff(call: PluginCall) {
        if (!granted()) return call.reject("Chưa cấp quyền lịch", "PERMISSION")
        try {
            val calendarId = ensureCalendarId()
            val ops = ArrayList<ContentProviderOperation>()
            val ins = call.getArray("insert") ?: JSArray()
            val upd = call.getArray("update") ?: JSArray()
            val del = call.getArray("delete") ?: JSArray()
            for (i in 0 until del.length()) {
                ops.add(ContentProviderOperation.newDelete(eventUri(del.getLong(i))).build())
            }
            for (i in 0 until upd.length()) {
                val o = upd.getJSONObject(i)
                ops.add(ContentProviderOperation.newUpdate(eventUri(o.getLong("eventId"))).withValues(eventValues(o, null)).build())
            }
            for (i in 0 until ins.length()) {
                ops.add(
                    ContentProviderOperation.newInsert(asSyncAdapter(Events.CONTENT_URI))
                        .withValues(eventValues(ins.getJSONObject(i), calendarId)).build()
                )
            }
            // chia nhỏ chỉ để không vượt giới hạn giao dịch Binder khi có hàng trăm việc
            for (chunk in ops.chunked(batchSize)) {
                context.contentResolver.applyBatch(CalendarContract.AUTHORITY, ArrayList(chunk))
            }
            call.resolve()
        } catch (e: Exception) {
            call.reject(e.message ?: "Lỗi ghi lịch", e)
        }
    }

    @PluginMethod
    fun removeAll(call: PluginCall) {
        if (!granted()) return call.reject("Chưa cấp quyền lịch", "PERMISSION")
        try {
            findCalendarId()?.let {
                context.contentResolver.delete(asSyncAdapter(ContentUris.withAppendedId(Calendars.CONTENT_URI, it)), null, null)
            }
            call.resolve()
        } catch (e: Exception) {
            call.reject(e.message ?: "Lỗi xóa lịch", e)
        }
    }
}
