const player = document.querySelector('#retest-player');

document.querySelectorAll('[data-seek]').forEach(link => {
  link.addEventListener('click', event => {
    if (!player || event.metaKey || event.ctrlKey || event.altKey || event.shiftKey) return;
    event.preventDefault();
    const seek = () => {
      player.currentTime = Number(link.dataset.seek);
      player.focus();
    };
    if (player.readyState >= HTMLMediaElement.HAVE_METADATA) {
      seek();
    } else {
      player.addEventListener('loadedmetadata', seek, {once: true});
      player.load();
    }
  });
});
