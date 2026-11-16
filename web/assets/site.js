'use strict';
const dialog = document.querySelector('#preview-dialog');
const openButton = document.querySelector('#open-preview');
const closeButton = document.querySelector('#close-preview');
openButton.addEventListener('click', () => dialog.showModal());
closeButton.addEventListener('click', () => dialog.close());
dialog.addEventListener('click', event => {
  if (event.target === dialog) {
    const rect = dialog.getBoundingClientRect();
    if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) dialog.close();
  }
});
fetch('build.json').then(response => {
  if (!response.ok) throw new Error('Build metadata unavailable');
  return response.json();
}).then(build => {
  document.querySelector('#build-id').textContent = `OpenSloper 0.2.0 · ${build.commit.slice(0, 7)}`;
}).catch(() => { /* The download page also works when opened offline. */ });
