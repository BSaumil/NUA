// IndexedDB setup for offline storage
const DB_NAME = 'SquarePOSDB';
const DB_VERSION = 1;

const initDB = () => {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);

    request.onupgradeneeded = (event) => {
      const db = event.target.result;

      // Create object stores
      if (!db.objectStoreNames.contains('products')) {
        db.createObjectStore('products', { keyPath: 'id' });
      }
      if (!db.objectStoreNames.contains('customers')) {
        db.createObjectStore('customers', { keyPath: 'id' });
      }
      if (!db.objectStoreNames.contains('transactions')) {
        db.createObjectStore('transactions', { keyPath: 'id' });
      }
      if (!db.objectStoreNames.contains('categories')) {
        db.createObjectStore('categories', { keyPath: 'id' });
      }
      if (!db.objectStoreNames.contains('printers')) {
        db.createObjectStore('printers', { keyPath: 'id' });
      }
      if (!db.objectStoreNames.contains('pending_sync')) {
        db.createObjectStore('pending_sync', { keyPath: 'id', autoIncrement: true });
      }
    };
  });
};

// Save data to IndexedDB
export const saveToIndexedDB = async (storeName, data) => {
  const db = await initDB();
  const transaction = db.transaction(storeName, 'readwrite');
  const store = transaction.objectStore(storeName);

  if (Array.isArray(data)) {
    data.forEach(item => store.put(item));
  } else {
    store.put(data);
  }

  return new Promise((resolve, reject) => {
    transaction.oncomplete = () => resolve();
    transaction.onerror = () => reject(transaction.error);
  });
};

// Get data from IndexedDB
export const getFromIndexedDB = async (storeName, key = null) => {
  const db = await initDB();
  const transaction = db.transaction(storeName, 'readonly');
  const store = transaction.objectStore(storeName);

  if (key) {
    return new Promise((resolve, reject) => {
      const request = store.get(key);
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  } else {
    return new Promise((resolve, reject) => {
      const request = store.getAll();
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }
};

// Add to pending sync queue
export const addToPendingSync = async (data) => {
  const db = await initDB();
  const transaction = db.transaction('pending_sync', 'readwrite');
  const store = transaction.objectStore('pending_sync');
  
  store.add({
    ...data,
    timestamp: new Date().toISOString()
  });

  return new Promise((resolve, reject) => {
    transaction.oncomplete = () => resolve();
    transaction.onerror = () => reject(transaction.error);
  });
};

// Get pending sync items
export const getPendingSync = async () => {
  return getFromIndexedDB('pending_sync');
};

// Clear pending sync after successful sync
export const clearPendingSync = async () => {
  const db = await initDB();
  const transaction = db.transaction('pending_sync', 'readwrite');
  const store = transaction.objectStore('pending_sync');
  store.clear();

  return new Promise((resolve, reject) => {
    transaction.oncomplete = () => resolve();
    transaction.onerror = () => reject(transaction.error);
  });
};

// Check if online
export const isOnline = () => {
  return navigator.onLine;
};

// Cache all data for offline use
export const cacheAllData = async (data) => {
  try {
    if (data.products) await saveToIndexedDB('products', data.products);
    if (data.customers) await saveToIndexedDB('customers', data.customers);
    if (data.categories) await saveToIndexedDB('categories', data.categories);
    if (data.printers) await saveToIndexedDB('printers', data.printers);
    console.log('✅ Data cached for offline use');
  } catch (error) {
    console.error('Error caching data:', error);
  }
};

// Sync offline data when back online
export const syncOfflineData = async (api) => {
  if (!isOnline()) {
    console.log('Still offline, cannot sync');
    return;
  }

  try {
    const pendingItems = await getPendingSync();
    
    if (pendingItems.length === 0) {
      console.log('No pending items to sync');
      return;
    }

    console.log(`Syncing ${pendingItems.length} offline items...`);
    
    for (const item of pendingItems) {
      if (item.type === 'transaction') {
        await api.post('/transactions', item.data);
      }
    }

    await clearPendingSync();
    console.log('✅ Offline data synced successfully');
    
    return true;
  } catch (error) {
    console.error('Error syncing offline data:', error);
    return false;
  }
};

export default {
  initDB,
  saveToIndexedDB,
  getFromIndexedDB,
  addToPendingSync,
  getPendingSync,
  clearPendingSync,
  isOnline,
  cacheAllData,
  syncOfflineData
};
