import '@testing-library/jest-dom/vitest';

// jsdom has no canvas; the Signal component treats a missing 2d context as "no display".
HTMLCanvasElement.prototype.getContext = () => null;
