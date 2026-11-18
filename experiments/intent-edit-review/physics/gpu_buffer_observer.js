// Test-only preload observer. No vertex/index/color uploads, attribute-pointer
// writes, shader edits or expected data are supplied by this hook.
(() => {
  if (!globalThis.WebGL2RenderingContext) {
    globalThis.__gpuBufferAudit = {unsupported: 'WebGL2RenderingContext unavailable'};
    return;
  }
  const original = WebGL2RenderingContext.prototype.drawElements;
  let sequence = 0, request = null, capture = null;
  const errors = [], objectIds = new WeakMap();
  let nextObjectId = 1;
  const id = object => {
    if (!object) return null;
    if (!objectIds.has(object)) objectIds.set(object, nextObjectId++);
    return objectIds.get(object);
  };
  const base64 = bytes => {
    let binary = '';
    for (let offset = 0; offset < bytes.length; offset += 32768)
      binary += String.fromCharCode(...bytes.subarray(offset, offset + 32768));
    return btoa(binary);
  };
  const insist = (condition, message) => {if (!condition) throw new Error(message);};
  globalThis.__gpuBufferAudit = {
    get sequence() {return sequence;},
    get errors() {return errors.slice();},
    arm(value) {
      insist(Number.isInteger(value.nv) && value.nv > 0 && Number.isInteger(value.nt) && value.nt > 0, 'Invalid cloth dimensions');
      request = Object.freeze({...value, afterSequence: sequence});
      capture = null;
      return sequence;
    },
    read() {return capture;}
  };
  WebGL2RenderingContext.prototype.drawElements = function(mode, count, type, offset) {
    // The real GL command is issued FIRST, with all original arguments/state.
    const result = Reflect.apply(original, this, arguments);
    sequence++;
    const expected = request;
    if (!expected || capture || mode !== this.TRIANGLES || count !== expected.nt * 3) return result;
    const info = globalThis.physicsReview?.info?.();
    if (!info || info.case !== expected.case || info.index !== expected.frame || info.mode !== expected.mode) return result;
    try {
      const gl = this, program = gl.getParameter(gl.CURRENT_PROGRAM);
      insist(program, 'No active program after actual cloth drawElements');
      const location = gl.getAttribLocation(program, 'color');
      insist(location >= 0, 'Actual draw program has no active color attribute');
      const attribute = {
        location,
        enabled: gl.getVertexAttrib(location, gl.VERTEX_ATTRIB_ARRAY_ENABLED),
        size: gl.getVertexAttrib(location, gl.VERTEX_ATTRIB_ARRAY_SIZE),
        type: gl.getVertexAttrib(location, gl.VERTEX_ATTRIB_ARRAY_TYPE),
        normalized: gl.getVertexAttrib(location, gl.VERTEX_ATTRIB_ARRAY_NORMALIZED),
        stride: gl.getVertexAttrib(location, gl.VERTEX_ATTRIB_ARRAY_STRIDE),
        offset: gl.getVertexAttribOffset(location, gl.VERTEX_ATTRIB_ARRAY_POINTER),
        divisor: gl.getVertexAttrib(location, gl.VERTEX_ATTRIB_ARRAY_DIVISOR),
        integer: gl.getVertexAttrib(location, gl.VERTEX_ATTRIB_ARRAY_INTEGER)
      };
      insist(attribute.enabled && attribute.size === 3 && attribute.type === gl.FLOAT, 'Cloth color layout is not enabled FLOAT vec3');
      insist(!attribute.normalized && !attribute.integer && attribute.divisor === 0, 'Unexpected normalized/integer/instanced color layout');
      // WebGL's tightly packed vec3 may use the implicit stride 0 or the
      // explicit equivalent 12 bytes. Read contiguous FLOAT triples only.
      insist((attribute.stride === 0 || attribute.stride === 12) && attribute.offset === 0,
        'Unexpected interleaved/offset color layout: ' + JSON.stringify(attribute));
      insist(offset === 0 && (type === gl.UNSIGNED_SHORT || type === gl.UNSIGNED_INT), 'Unexpected cloth index layout');
      const indexBytes = gl.getBufferParameter(gl.ELEMENT_ARRAY_BUFFER, gl.BUFFER_SIZE);
      insist(indexBytes === count * (type === gl.UNSIGNED_SHORT ? 2 : 4), 'Actual index buffer does not match complete cloth triangle draw');
      const buffer = gl.getVertexAttrib(location, gl.VERTEX_ATTRIB_ARRAY_BUFFER_BINDING);
      insist(buffer, 'Active color attribute has no bound GL buffer');
      const prior = gl.getParameter(gl.ARRAY_BUFFER_BINDING);
      const values = new Float32Array(expected.nv * 3);
      let byteLength, restored = false;
      try {
        gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
        byteLength = gl.getBufferParameter(gl.ARRAY_BUFFER, gl.BUFFER_SIZE);
        insist(byteLength === values.byteLength, 'Color VBO is not nv*3 float32 values');
        gl.getBufferSubData(gl.ARRAY_BUFFER, 0, values);
      } finally {
        gl.bindBuffer(gl.ARRAY_BUFFER, prior);
        restored = gl.getParameter(gl.ARRAY_BUFFER_BINDING) === prior;
      }
      insist(restored, 'ARRAY_BUFFER binding was not restored after GL readback');
      insist(values.every(Number.isFinite), 'Actual GL color buffer has nonfinite values');
      const debug = gl.getExtension('WEBGL_debug_renderer_info');
      capture = {
        token: expected.token, sequence, afterSequence: expected.afterSequence,
        case: info.case, frame: info.index, mode: info.mode,
        draw: {method: 'WebGL2.drawElements', mode, count, type, offset, indexBytes},
        attribute, color_buffer: id(buffer), program: id(program), context: id(gl),
        byte_length: byteLength, float_count: values.length, array_buffer_restored: restored,
        context_info: {
          version: gl.getParameter(gl.VERSION), shading_language: gl.getParameter(gl.SHADING_LANGUAGE_VERSION),
          vendor: gl.getParameter(gl.VENDOR), renderer: gl.getParameter(gl.RENDERER),
          unmasked_vendor: debug ? gl.getParameter(debug.UNMASKED_VENDOR_WEBGL) : null,
          unmasked_renderer: debug ? gl.getParameter(debug.UNMASKED_RENDERER_WEBGL) : null,
          attributes: gl.getContextAttributes(), context_lost: gl.isContextLost()
        },
        color_float32_base64: base64(new Uint8Array(values.buffer))
      };
    } catch (error) {
      const entry = {token: expected.token, sequence, error: String(error)};
      errors.push(entry); capture = entry;
    }
    return result;
  };
})();
