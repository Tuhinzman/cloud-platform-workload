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
]
