import js from '@eslint/js';
import prettier from 'eslint-config-prettier';
import tseslint from 'typescript-eslint';
import { defineConfig } from 'eslint/config';

export default defineConfig(
  { ignores: ['dist/', 'scripts/', 'node_modules/', 'playwright-report/', 'test-results/'] },
  js.configs.recommended,
  ...tseslint.configs.strictTypeChecked,
  ...tseslint.configs.stylisticTypeChecked,
  {
    languageOptions: {
      parserOptions: { projectService: true, tsconfigRootDir: import.meta.dirname },
    },
    rules: {
      // Feed data is untrusted; forbid the one API that would let it become markup.
      'no-restricted-properties': [
        'error',
        { property: 'innerHTML', message: 'Use ui/dom.ts builders (textContent) instead.' },
        { property: 'outerHTML', message: 'Use ui/dom.ts builders instead.' },
      ],
      'no-restricted-syntax': [
        'error',
        {
          selector: "CallExpression[callee.property.name='insertAdjacentHTML']",
          message: 'Use ui/dom.ts builders instead.',
        },
      ],
      '@typescript-eslint/no-unnecessary-condition': 'off',
      // Feed strings may be '' and must fall back to a label, so || is the intended operator there.
      '@typescript-eslint/prefer-nullish-coalescing': ['error', { ignorePrimitives: { string: true } }],
      '@typescript-eslint/no-confusing-void-expression': ['error', { ignoreArrowShorthand: true }],
      '@typescript-eslint/restrict-template-expressions': ['error', { allowNumber: true }],
    },
  },
  {
    files: ['**/*.test.ts', '**/*.test.tsx', 'vite.config.ts'],
    rules: {
      '@typescript-eslint/no-unsafe-assignment': 'off',
      '@typescript-eslint/no-non-null-assertion': 'off',
      // Test fixtures build their own scaffolding; the innerHTML ban is for app code.
      'no-restricted-properties': 'off',
    },
  },
  prettier,
);
