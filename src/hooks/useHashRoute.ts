import { useCallback, useEffect, useState } from 'react';

export type Route =
  | { name: 'home' }
  | { name: 'upload' }
  | { name: 'report'; reportId: string };

export function parseHash(hash: string): Route {
  const path = hash.replace(/^#/, '') || '/';
  const match = path.match(/^\/report\/(rep_[0-9a-f]{8,32})$/);
  if (match) return { name: 'report', reportId: match[1] };
  if (path === '/upload') return { name: 'upload' };
  return { name: 'home' };
}

export function routeToHash(route: Route): string {
  if (route.name === 'report') return `#/report/${route.reportId}`;
  if (route.name === 'upload') return '#/upload';
  return '#/';
}

export function useHashRoute(): [Route, (route: Route) => void] {
  const [route, setRoute] = useState<Route>(() => parseHash(window.location.hash));

  useEffect(() => {
    const onChange = () => {
      setRoute(parseHash(window.location.hash));
      window.scrollTo({ top: 0 });
    };
    window.addEventListener('hashchange', onChange);
    return () => window.removeEventListener('hashchange', onChange);
  }, []);

  const navigate = useCallback((next: Route) => {
    const hash = routeToHash(next);
    if (window.location.hash !== hash) window.location.hash = hash;
    else setRoute(next);
  }, []);

  return [route, navigate];
}