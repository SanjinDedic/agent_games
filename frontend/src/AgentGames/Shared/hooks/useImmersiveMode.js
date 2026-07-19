import { useCallback, useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import {
  selectImmersiveMode,
  setImmersiveMode,
} from '../../../slices/settingsSlice';

/**
 * Immersive mode for the submission workspaces: browser fullscreen plus a
 * hidden navbar (Navbar.jsx returns null while the flag is set). Redux holds
 * the flag so the navbar — a sibling of the page — can react to it.
 *
 * Mount this exactly once per page (CombinedFooter does). The browser is the
 * source of truth while real fullscreen is active: ESC/F11 fire
 * `fullscreenchange`, which syncs the flag back. If the Fullscreen API is
 * unavailable or refuses (e.g. embedded in an iframe), we still hide the
 * navbar so students get most of the benefit.
 */
function useImmersiveMode() {
  const dispatch = useDispatch();
  const isImmersive = useSelector(selectImmersiveMode);

  useEffect(() => {
    const syncWithBrowser = () => {
      dispatch(setImmersiveMode(!!document.fullscreenElement));
    };
    document.addEventListener('fullscreenchange', syncWithBrowser);

    return () => {
      document.removeEventListener('fullscreenchange', syncWithBrowser);
      // Leaving the page restores the navbar and drops fullscreen
      if (document.fullscreenElement) {
        document.exitFullscreen().catch(() => {});
      }
      dispatch(setImmersiveMode(false));
    };
  }, [dispatch]);

  const toggleImmersive = useCallback(async () => {
    if (isImmersive) {
      if (document.fullscreenElement) {
        try {
          await document.exitFullscreen();
        } catch {
          /* fall through to clearing the flag */
        }
      }
      dispatch(setImmersiveMode(false));
    } else {
      try {
        await document.documentElement.requestFullscreen?.();
      } catch {
        /* fullscreen refused — navbar-hiding alone is still worthwhile */
      }
      dispatch(setImmersiveMode(true));
    }
  }, [dispatch, isImmersive]);

  return { isImmersive, toggleImmersive };
}

export default useImmersiveMode;
