(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.VeriAbstainCore = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  function stable(value) {
    if (Array.isArray(value)) return value.map(stable);
    if (value && typeof value === 'object') {
      return Object.keys(value).sort().reduce((result, key) => {
        result[key] = stable(value[key]);
        return result;
      }, {});
    }
    return value;
  }

  function canonical(value) {
    return JSON.stringify(stable(value));
  }

  async function sha256Hex(value) {
    const bytes = new TextEncoder().encode(typeof value === 'string' ? value : canonical(value));
    const digest = await crypto.subtle.digest('SHA-256', bytes);
    return '0x' + Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, '0')).join('');
  }

  function strip0x(value) {
    return String(value).replace(/^0x/i, '');
  }

  function padWord(value) {
    return strip0x(value).toLowerCase().padStart(64, '0');
  }

  function encodeAddressCall(selector, address) {
    if (!/^0x[0-9a-fA-F]{40}$/.test(address)) throw new Error('Invalid address');
    return selector + padWord(address);
  }

  function encodeAddressBytes32Call(selector, address, digest) {
    if (!/^0x[0-9a-fA-F]{64}$/.test(digest)) throw new Error('Invalid digest');
    return selector + padWord(address) + strip0x(digest).toLowerCase();
  }

  function buildRecordCalldata(selector, evidenceDigest, assessmentDigest) {
    if (!/^0x[0-9a-fA-F]{64}$/.test(evidenceDigest) || !/^0x[0-9a-fA-F]{64}$/.test(assessmentDigest)) {
      throw new Error('Invalid receipt digest');
    }
    return selector + strip0x(evidenceDigest).toLowerCase() + strip0x(assessmentDigest).toLowerCase();
  }

  function decodeUint(value) {
    if (!/^0x[0-9a-fA-F]{64}$/.test(value)) throw new Error('Malformed uint response');
    return BigInt(value);
  }

  function decodeBool(value) {
    const decoded = decodeUint(value);
    if (decoded !== 0n && decoded !== 1n) throw new Error('Malformed bool response');
    return decoded === 1n;
  }

  function decodeAddress(value) {
    if (!/^0x[0-9a-fA-F]{64}$/.test(value) || !/^0{24}[0-9a-fA-F]{40}$/.test(value.slice(2))) {
      throw new Error('Malformed address response');
    }
    return '0x' + value.slice(-40);
  }

  function shorten(value, start = 6, end = 4) {
    if (!value) return '—';
    return value.length <= start + end + 3 ? value : `${value.slice(0, start)}…${value.slice(-end)}`;
  }

  return Object.freeze({
    canonical,
    sha256Hex,
    encodeAddressCall,
    encodeAddressBytes32Call,
    buildRecordCalldata,
    decodeUint,
    decodeBool,
    decodeAddress,
    shorten,
  });
});
