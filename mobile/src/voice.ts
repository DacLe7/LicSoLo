/* Ghi âm -> WAV 16 kHz mono 16 bit. Chép từ lichviet/ui.py (đối tượng Voice), chỉ bỏ phần giao diện. */

export class Recorder {
  private rec: MediaRecorder | null = null;
  private chunks: Blob[] = [];
  private stream: MediaStream | null = null;
  private timer: ReturnType<typeof setTimeout> | undefined;
  private finish: ((b: Blob | null) => void) | null = null;
  on = false;

  static supported() {
    return !!navigator.mediaDevices?.getUserMedia && typeof MediaRecorder !== "undefined";
  }

  /** Bắt đầu ghi; trả về Promise kết thúc khi stop() được gọi hoặc quá 20 giây. null nếu quá ngắn. */
  async start(): Promise<Blob | null> {
    this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    this.chunks = [];
    const r = (this.rec = new MediaRecorder(this.stream));
    r.ondataavailable = (e) => { if (e.data.size) this.chunks.push(e.data); };
    const done = new Promise<Blob | null>((res) => (this.finish = res));
    r.onstop = () => {
      this.on = false;
      this.stream?.getTracks().forEach((t) => t.stop());
      const blob = new Blob(this.chunks, { type: r.mimeType });
      this.finish?.(blob.size < 2000 ? null : blob);
    };
    r.start();
    this.on = true;
    this.timer = setTimeout(() => this.stop(), 20_000);
    return done;
  }

  stop() {
    clearTimeout(this.timer);
    if (this.rec && this.rec.state !== "inactive") this.rec.stop();
  }
}

export async function toWav(blob: Blob): Promise<ArrayBuffer> {
  const ac = new AudioContext();
  const buf = await ac.decodeAudioData(await blob.arrayBuffer());
  void ac.close();
  const n = Math.max(1, Math.ceil(buf.duration * 16000));
  const oc = new OfflineAudioContext(1, n, 16000);
  const src = oc.createBufferSource();
  src.buffer = buf;
  src.connect(oc.destination);
  src.start();
  const pcm = (await oc.startRendering()).getChannelData(0);
  const out = new DataView(new ArrayBuffer(44 + pcm.length * 2));
  const w = (o: number, t: string) => { for (let i = 0; i < t.length; i++) out.setUint8(o + i, t.charCodeAt(i)); };
  w(0, "RIFF"); out.setUint32(4, 36 + pcm.length * 2, true); w(8, "WAVEfmt "); out.setUint32(16, 16, true);
  out.setUint16(20, 1, true); out.setUint16(22, 1, true); out.setUint32(24, 16000, true); out.setUint32(28, 32000, true);
  out.setUint16(32, 2, true); out.setUint16(34, 16, true); w(36, "data"); out.setUint32(40, pcm.length * 2, true);
  for (let i = 0; i < pcm.length; i++) {
    const v = Math.max(-1, Math.min(1, pcm[i]));
    out.setInt16(44 + i * 2, v < 0 ? v * 32768 : v * 32767, true);
  }
  return out.buffer;
}

export function toBase64(buf: ArrayBuffer): string {
  const bytes = new Uint8Array(buf);
  let s = "";
  for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  return btoa(s);
}
