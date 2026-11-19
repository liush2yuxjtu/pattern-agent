import {createSimulation} from './solver-corrector.js';

export async function createCorrector(document, body, options) {
  // The HTML build embeds the worker so downloads work without a server.
  if (typeof GARMENT_CORRECTOR_WORKER !== 'undefined' && typeof Worker !== 'undefined') {
    const url = URL.createObjectURL(new Blob([GARMENT_CORRECTOR_WORKER], {type: 'text/javascript'}));
    let worker, pending, failure;
    function fail(error) {
      failure = error;
      pending?.reject(error);
      pending = null;
    }
    function send(data, transfer = []) {
      return new Promise((resolve, reject) => {
        if (failure) { reject(failure); return; }
        if (pending) { reject(new Error('Cloth corrector is already running')); return; }
        pending = {resolve, reject};
        try { worker.postMessage(data, transfer); }
        catch (error) { fail(error); }
      });
    }
    try {
      worker = new Worker(url, {name: 'garment-corrector'});
      worker.onmessage = ({data}) => {
        const request = pending;
        pending = null;
        if (data.error) request?.reject(new Error(data.error));
        else request?.resolve(data.positions);
      };
      worker.onerror = event => fail(new Error(event.message || 'Cloth corrector worker failed'));
      worker.onmessageerror = () => fail(new Error('Cloth corrector worker response could not be read'));
      await send({type: 'init', document, body, options});
      return {
        thread: 'worker',
        step: (positions, pinned) => send({type: 'step', positions, pinned}, [positions.buffer]),
        dispose() {
          worker.terminate();
          fail(new Error('Disposed cloth corrector'));
        },
      };
    } catch {
      worker?.terminate();
      // Keep simulation available where dedicated blob workers are restricted.
    } finally {
      URL.revokeObjectURL(url);
    }
  }
  const corrector = createSimulation(document, body, options);
  return {
    thread: 'main',
    step(positions, pinned) {
      corrector.setPositions(positions);
      corrector.setPinned(pinned);
      return corrector.step();
    },
    dispose: () => corrector.dispose(),
  };
}
