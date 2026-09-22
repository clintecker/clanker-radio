import { render } from 'preact';
import { LocationProvider, Route, Router, lazy } from 'preact-iso';
import './styles/console.css';
import { DEBUG_ENABLED, parseDebug } from './debug';
import { applyTextures } from './design/textures';
import { ConsoleLive } from './pages/console/ConsoleLive';

const Kit = import.meta.env.DEV ? lazy(() => import('./pages/console/Kit').then((m) => m.Kit)) : null;

function NotFound() {
  return (
    <div class="rack console">
      <div class="rack-inner">
        <p class="engr">No such frequency.</p>
        <a class="key" href="/">
          Back to the live band
        </a>
      </div>
    </div>
  );
}

export function ConsoleApp() {
  return (
    <LocationProvider>
      <Router>
        <Route path="/" component={ConsoleLive} />
        <Route path="/__kit" component={Kit ?? NotFound} />
        <Route default component={NotFound} />
      </Router>
    </LocationProvider>
  );
}

export function mountConsole(root: HTMLElement): void {
  const html = document.documentElement;
  html.dataset.ui = 'console';
  const meta = document.querySelector('meta[name="theme-color"]');
  meta?.setAttribute('content', '#05070A');
  if (DEBUG_ENABLED) {
    const vw = parseDebug(location.search).vw;
    if (vw) {
      html.dataset.vw = String(vw);
      html.style.setProperty('--vw', `${vw}px`);
    }
  }
  applyTextures(html);
  render(<ConsoleApp />, root);
}
