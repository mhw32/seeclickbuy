import { createRoot } from 'react-dom/client';
import App from '@src/App';
// eslint-disable-next-line
// @ts-ignore
import injectedStyle from '@src/index.css?inline';

export function mount() {
  const root = document.createElement('div');
  root.id = 'chrome-extension-boilerplate-react-vite-runtime-content-view-root';

  // Create shadow root structure
  const rootIntoShadow = document.createElement('div');
  rootIntoShadow.id = 'shadow-root';
  const shadowRoot = root.attachShadow({ mode: 'open' });

  // Handle Firefox style injection
  if (navigator.userAgent.includes('Firefox')) {
    const styleElement = document.createElement('style');
    styleElement.innerHTML = injectedStyle;
    shadowRoot.appendChild(styleElement);
  } else {
    const globalStyleSheet = new CSSStyleSheet();
    globalStyleSheet.replaceSync(injectedStyle);
    shadowRoot.adoptedStyleSheets = [globalStyleSheet];
  }

  // Append elements
  document.body.appendChild(root);
  shadowRoot.appendChild(rootIntoShadow);
  createRoot(rootIntoShadow).render(<App />);
}