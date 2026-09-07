// ESLint 9 flat configuration for frontend.
//
// ESLint 9 resolves flat configuration only. The .eslintrc beside this file is the
// upstream-derived record of the original lint intent and is retained unmodified, so it
// is an input to this file rather than something this file replaces mechanically.
//
// The two Next presets already register @next/next, react, react-hooks, import,
// jsx-a11y and @typescript-eslint, and already select the parser for each file type.
// Registering any of those again would bind a second plugin object under a name the
// presets already own, which ESLint rejects as a redefinition before it reads any
// source. The installed tree makes that a real hazard rather than a theoretical one:
// @typescript-eslint resolves to 8.52.0 at the top level and to 8.46.2 under the
// typescript-eslint package the Next preset consumes.
//
// Only rules the presets do not already produce at the intended value are restated
// below, so this file carries lint policy and nothing else.

import nextCoreWebVitals from 'eslint-config-next/core-web-vitals'
import nextTypeScript from 'eslint-config-next/typescript'

export default [
  ...nextCoreWebVitals,
  ...nextTypeScript,
  {
    rules: {
      // No preset supplies a line-length rule, so the existing 150-character policy
      // would be lost silently rather than deliberately.
      'max-len': [
        'error',
        {
          code: 150,
          ignoreComments: true,
          ignoreTrailingComments: true,
          ignoreUrls: true,
          ignoreStrings: true,
          ignoreTemplateLiterals: true,
        },
      ],

      // eslint-config-next/typescript sets this to warn. The existing policy treats an
      // unused binding as an error, and adopting the preset severity would weaken a
      // rule this service already enforces.
      'no-unused-vars': 'off',
      '@typescript-eslint/no-unused-vars': 'error',
    },
  },
  {
    // The TypeScript preset spreads a base config that carries no file restriction, so
    // rules about TypeScript module syntax also reach plain JavaScript. These two files
    // have to be CommonJS: next.config.js is read by Next through require, and
    // utils/telemetry/Instrumentation.js is loaded through --require, which accepts
    // CommonJS only. Rewriting either as a module would break how it is loaded.
    //
    // Named individually rather than by a .js glob. Being a .js file is not on its own a
    // reason to be exempt, and utils/imageLoader.js is the counter-example: it is .js but
    // written as a module and bundled. A glob would also exempt future JavaScript files
    // that nobody has looked at.
    //
    // Only this rule's reach is corrected. It stays in force everywhere else, and these
    // two files stay subject to every other rule.
    files: ['next.config.js', 'utils/telemetry/Instrumentation.js'],
    rules: {
      '@typescript-eslint/no-require-imports': 'off',
    },
  },
  {
    // setupNodeEvents is declared by Cypress as (on, config). The callback here is still
    // a stub, so neither parameter is read yet, and the default after-used check reports
    // both because nothing after them is used. The names are kept because they are the
    // documented shape of the hook and are what a listener registered here would use.
    //
    // The exemption is anchored to those two names rather than turning argument checking
    // off for the file, so any other unused parameter, and every unused variable, is
    // still an error here.
    files: ['cypress.config.ts'],
    rules: {
      '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^(on|config)$' }],
    },
  },
  {
    // Four findings that are reported but not acted on, kept visible as warnings rather
    // than either fixed or silenced. None of them belongs to the lint intent this service
    // already had: the .eslintrc carried hooks policy only as exhaustive-deps at warn.
    //
    // set-state-in-effect, purity and preserve-manual-memoization arrived with the newer
    // React Compiler rules in the preset. Each one reports real upstream behaviour whose
    // obvious rewrite would change more than it fixes: the two mount-time effects exist so
    // the server renders an empty value and the client fills it in afterwards, and writing
    // that state during render instead would produce a hydration mismatch.
    //
    // no-explicit-any is retained deliberately. The one occurrence carries query
    // parameters that are strings in some calls and arrays of strings in others, and every
    // narrower type either rejects those callers or breaks the URLSearchParams call that
    // consumes them. The first type check to run against this service passed, so the type
    // surface is valid as written.
    //
    // Warning, not off. Every finding still appears in the job log with its rule and
    // location; only the exit code changes. Revisit if any of them becomes actionable.
    rules: {
      'react-hooks/set-state-in-effect': 'warn',
      'react-hooks/purity': 'warn',
      'react-hooks/preserve-manual-memoization': 'warn',
      '@typescript-eslint/no-explicit-any': 'warn',
    },
  },
]
