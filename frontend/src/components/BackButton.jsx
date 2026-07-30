import React, { useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useTheme } from '../contexts/ThemeContext';
import { QUICK_ACTIONS } from './BottomDock';

// Same "front door" logic ProtectedRoutes uses to pick where a role lands —
// that's also where Back should bottom out once there's nothing earlier to
// go to (e.g. after a page refresh, or backing out of the whole nav stack).
function roleHome(role) {
  if (role === 'cashier') return '/pos';
  if (role === 'kitchen') return '/kitchen';
  return '/today';
}

export default function BackButton() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { theme, darkMode } = useTheme();
  const stackRef = useRef([location.pathname]);
  const [, forceRender] = useState(0);

  useEffect(() => {
    const stack = stackRef.current;
    if (stack[stack.length - 1] !== location.pathname) {
      stack.push(location.pathname);
    }
    forceRender(n => n + 1);
  }, [location.pathname]);

  if (!user) return null;
  const quickPaths = (QUICK_ACTIONS[user.role] || QUICK_ACTIONS.cashier).map(q => q.path);
  // Nothing to back out of — already on one of the role's main destinations.
  if (quickPaths.includes(location.pathname)) return null;

  const goBack = () => {
    const stack = stackRef.current;
    const home = roleHome(user.role);
    if (stack.length >= 2) {
      stack.pop();
      navigate(stack[stack.length - 1]);
    } else {
      stackRef.current = [home];
      navigate(home);
    }
  };

  return (
    <button
      onClick={goBack}
      className={`flex items-center gap-1.5 mb-3 text-sm font-medium rounded-lg px-2.5 py-1.5 -ml-2.5 transition-colors ${darkMode ? 'hover:bg-white/10' : 'hover:bg-black/5'}`}
      style={{ color: darkMode ? '#d4d4d8' : theme.text }}
      data-testid="back-button"
    >
      <ArrowLeft size={16} /> Back
    </button>
  );
}
