import 'webextension-polyfill';
import { exampleThemeStorage, profileStorage } from '@extension/storage';

exampleThemeStorage.get().then(theme => {
  console.log('theme', theme);
});

profileStorage.get().then(profile => {
  console.log('profile', profile);
});

console.log('background loaded');
console.log("Edit 'chrome-extension/src/background/index.ts' and save to reload.");
