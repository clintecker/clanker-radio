import { STREAM_CORS_OK, defaultStream, streams, type StreamOption } from './config';
import type { PlaybackTiming } from './listener-delay';

export type PlayerState = 'idle' | 'loading' | 'playing' | 'error';

export interface PlayerSnapshot {
  state: PlayerState;
  stream: StreamOption;
  volume: number;
  volumeSupported: boolean;
}

type Listener = (snap: PlayerSnapshot) => void;

/**
 * Wraps the <audio> element for the live stream.
 *
 * Deliberately no autoplay: the old page started every visitor muted-but-streaming,
 * which pulled audio for people who never tuned in and counted each page view as
 * an Icecast listener. Nothing is fetched until the listener presses TUNE IN.
 */
export class Player {
  private readonly audio: HTMLAudioElement;
  private state: PlayerState = 'idle';
  private stream: StreamOption = defaultStream;
  private volume = 0.7;
  private readonly listeners = new Set<Listener>();
  private context: AudioContext | null = null;
  private analyser: AnalyserNode | null = null;
  /** Date.now() when the current stream connection was requested; null when stopped. */
  private connectedAtMs: number | null = null;
  /** True once this connection has produced audio (so later stalls still count as tuned in). */
  private started = false;

  constructor(audio: HTMLAudioElement) {
    this.audio = audio;
    audio.preload = 'none';
    // CORS mode lets Web Audio read the samples; without a valid ACAO header it would block playback.
    if (STREAM_CORS_OK) audio.crossOrigin = 'anonymous';
    audio.addEventListener('playing', () => {
      this.started = true;
      this.set('playing');
    });
    audio.addEventListener('waiting', () => this.set('loading'));
    audio.addEventListener('stalled', () => this.set('loading'));
    audio.addEventListener('pause', () => this.set('idle'));
    audio.addEventListener('error', () => this.set('error'));
    try {
      const saved = localStorage.getItem('radio.volume');
      if (saved !== null) this.volume = Math.min(1, Math.max(0, Number(saved)));
      const savedStream = localStorage.getItem('radio.stream');
      this.stream = streams.find((s) => s.path === savedStream) ?? defaultStream;
    } catch {
      /* storage blocked; defaults are fine */
    }
    audio.volume = this.volume;
  }

  /** iOS Safari ignores audio.volume entirely; hide the slider there rather than show a dead control. */
  get volumeSupported(): boolean {
    return !/iPad|iPhone|iPod/.test(navigator.userAgent);
  }

  snapshot(): PlayerSnapshot {
    return { state: this.state, stream: this.stream, volume: this.volume, volumeSupported: this.volumeSupported };
  }

  subscribe(l: Listener): () => void {
    this.listeners.add(l);
    l(this.snapshot());
    return () => this.listeners.delete(l);
  }

  async toggle(): Promise<void> {
    if (this.state === 'playing' || this.state === 'loading') this.stop();
    else await this.play();
  }

  async play(): Promise<void> {
    this.set('loading');
    // Live streams must not resume from a buffered position: always reload the source.
    this.connectedAtMs = Date.now();
    this.started = false;
    this.audio.src = this.stream.path;
    this.audio.load();
    try {
      await this.audio.play();
      await this.context?.resume();
    } catch (err) {
      console.warn('Playback failed', err);
      this.set('error');
    }
  }

  stop(): void {
    this.connectedAtMs = null;
    this.started = false;
    this.audio.pause();
    // Drop the connection so Icecast stops counting us and the buffer does not grow.
    this.audio.removeAttribute('src');
    this.audio.load();
    this.set('idle');
  }

  /**
   * What the delay estimator needs, or null when the listener is not hearing the
   * stream (stopped, errored, or still connecting). A stall after playback began
   * still returns timing: the listener is falling further behind.
   */
  timing(): PlaybackTiming | null {
    if (this.connectedAtMs === null || !this.started) return null;
    if (this.state === 'idle' || this.state === 'error') return null;
    return { connectedAtMs: this.connectedAtMs, currentTime: this.audio.currentTime, bitrateKbps: this.stream.bitrate };
  }

  setVolume(v: number): void {
    this.volume = Math.min(1, Math.max(0, v));
    this.audio.volume = this.volume;
    try {
      localStorage.setItem('radio.volume', String(this.volume));
    } catch {
      /* ignore */
    }
    this.emit();
  }

  async setStream(path: string): Promise<void> {
    const next = streams.find((s) => s.path === path);
    if (!next || next.path === this.stream.path) return;
    this.stream = next;
    try {
      localStorage.setItem('radio.stream', next.path);
    } catch {
      /* ignore */
    }
    if (this.state === 'playing' || this.state === 'loading') await this.play();
    else this.emit();
  }

  /**
   * Lazily attach a Web Audio analyser for the signal display. Created on first
   * playback (inside a user gesture) so the AudioContext is allowed to start.
   * Returns null where Web Audio is unavailable; the display then falls back to noise.
   */
  getAnalyser(): AnalyserNode | null {
    if (this.analyser) return this.analyser;
    const Ctx =
      window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!Ctx) return null;
    try {
      this.context = new Ctx();
      const src = this.context.createMediaElementSource(this.audio);
      this.analyser = this.context.createAnalyser();
      this.analyser.fftSize = 128;
      this.analyser.smoothingTimeConstant = 0.8;
      src.connect(this.analyser);
      this.analyser.connect(this.context.destination);
      return this.analyser;
    } catch (err) {
      console.warn('Web Audio unavailable; signal display will idle', err);
      return null;
    }
  }

  private set(state: PlayerState): void {
    if (this.state === state) return;
    this.state = state;
    this.emit();
  }

  private emit(): void {
    const snap = this.snapshot();
    for (const l of this.listeners) l(snap);
  }
}
