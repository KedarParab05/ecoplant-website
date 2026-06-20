async function withRetry(fn, options = {}) {
  const retries = options.retries ?? 2;
  const baseDelayMs = options.baseDelayMs ?? 450;

  let lastError;
  for (let attempt = 0; attempt <= retries; attempt += 1) {
    try {
      return await fn(attempt);
    } catch (error) {
      lastError = error;
      const retryable = error.status === 429 || error.status >= 500 || /quota|timeout|network/i.test(error.message || '');
      if (attempt === retries || !retryable) break;
      const delay = baseDelayMs * Math.pow(2, attempt);
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }

  throw lastError;
}

module.exports = { withRetry };
