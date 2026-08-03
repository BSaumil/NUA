/**
 * Coursing helpers for the POS cart.
 *
 * Mirrors `backend/services/coursing.py`. The server is authoritative — it
 * re-assigns courses on send — but the cart has to show the same answer while
 * the server is still typing, so the two must agree.
 */

/** Which course a category maps to, falling back to the venue's default. */
export function courseForCategory(category, config) {
  const fallback = config?.defaultCourse ?? 1;
  if (!category) return fallback;
  const map = config?.categoryCourses || {};
  const wanted = String(category).trim().toLowerCase();
  for (const [cat, key] of Object.entries(map)) {
    if (String(cat).trim().toLowerCase() === wanted) {
      const n = parseInt(key, 10);
      return Number.isNaN(n) ? fallback : n;
    }
  }
  return fallback;
}

/** Valid course keys, sorted. */
export function courseKeys(config) {
  const keys = (config?.courses || [])
    .map(c => parseInt(c.key, 10))
    .filter(n => !Number.isNaN(n));
  return [...new Set(keys)].sort((a, b) => a - b);
}

export function courseLabel(key, config) {
  const hit = (config?.courses || []).find(c => Number(c.key) === Number(key));
  return hit?.label || `Course ${key}`;
}

/**
 * The course a cart line belongs to. An explicit `course` set by the server on
 * the POS wins over the category default — they moved it there on purpose.
 */
export function lineCourse(item, config) {
  const valid = courseKeys(config);
  const fallback = config?.defaultCourse ?? 1;
  const explicit = item?.course;
  let course;
  if (explicit !== undefined && explicit !== null && String(explicit) !== '') {
    const n = parseInt(explicit, 10);
    course = Number.isNaN(n) ? courseForCategory(item?.category, config) : n;
  } else {
    course = courseForCategory(item?.category, config);
  }
  return valid.includes(course) ? course : fallback;
}

/** Cart grouped into courses, in course order. Empty courses are omitted. */
export function groupCartByCourse(cart, config) {
  const buckets = new Map();
  (cart || []).forEach(item => {
    const key = lineCourse(item, config);
    if (!buckets.has(key)) buckets.set(key, []);
    buckets.get(key).push(item);
  });
  return [...buckets.entries()]
    .sort((a, b) => a[0] - b[0])
    .map(([key, items]) => ({ key, label: courseLabel(key, config), items }));
}

/** Does this order bypass coursing entirely? */
export function isStraightFire(orderType, config, requested = false) {
  if (!config?.enabled) return true;
  if (requested) return true;
  const types = (config?.straightFireOrderTypes || []).map(t => String(t).toLowerCase());
  const ot = String(orderType || '').toLowerCase();
  return types.includes(ot) || types.includes(ot.replace('-', '_')) || types.includes(ot.replace('_', '-'));
}

/**
 * Should the POS show course UI at all right now?
 *
 * Off for a venue that hasn't enabled coursing, and off for order types that
 * always straight-fire — a takeaway counter shouldn't be picking courses.
 */
export function showCourseUI(orderType, config) {
  return !!config?.enabled && !isStraightFire(orderType, config, false);
}

/** Fire/hold state of a course on a live kitchen order. */
export function courseStatus(order, key) {
  return order?.courses?.[String(key)]?.status || 'queued';
}
