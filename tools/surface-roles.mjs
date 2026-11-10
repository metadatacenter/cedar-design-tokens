import * as sass from 'sass';

export function surfaceRoles() {
  const css = sass.compile(new URL('../surfaces/roles.scss', import.meta.url).pathname).css;
  return Object.fromEntries(
    [...css.matchAll(/\.([\w-]+)\s*\{([^}]+)\}/g)].map(([, role, body]) => [
      role,
      Object.fromEntries(
        [...body.matchAll(/([\w-]+):\s*([^;]+);/g)].map(([, property, value]) => [
          // These recipes use background only for a color; the walk reports its longhand.
          property === 'background' ? 'background-color' : property,
          value.trim(),
        ]),
      ),
    ]),
  );
}
