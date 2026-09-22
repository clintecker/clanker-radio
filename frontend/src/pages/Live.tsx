import { History, Queue } from '../components/TrackList';
import { NowPlaying } from '../components/NowPlaying';
import { Receiver } from '../components/Receiver';

export function Live() {
  return (
    <>
      <NowPlaying />
      <Receiver />
      <Queue />
      <History />
    </>
  );
}
