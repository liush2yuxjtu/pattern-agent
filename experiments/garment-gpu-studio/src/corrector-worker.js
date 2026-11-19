import {createSimulation} from './solver-corrector.js';

let corrector;
self.onmessage = ({data}) => {
  try {
    if (data.type === 'init') {
      corrector = createSimulation(data.document, data.body, data.options);
      self.postMessage({});
      return;
    }
    const {positions, pinned} = data;
    corrector.setPositions(positions);
    corrector.setPinned(pinned);
    positions.set(corrector.step());
    self.postMessage({positions}, [positions.buffer]);
  } catch (error) {
    self.postMessage({error: error.message});
  }
};
