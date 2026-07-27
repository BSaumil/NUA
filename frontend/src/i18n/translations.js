// Lightweight i18n for customer-facing surfaces (Customer Display, Kiosk,
// QR table ordering, Online ordering). Not used by the staff-facing app —
// those pages are a separate concern with their own language (English).

export const LANGUAGES = [
  { code: 'en', label: 'English', dir: 'ltr' },
  { code: 'it', label: 'Italiano', dir: 'ltr' },
  { code: 'zh', label: '中文', dir: 'ltr' },
  { code: 'hi', label: 'हिन्दी', dir: 'ltr' },
  { code: 'es', label: 'Español', dir: 'ltr' },
  { code: 'vi', label: 'Tiếng Việt', dir: 'ltr' },
  { code: 'ar', label: 'العربية', dir: 'rtl' },
  { code: 'pt', label: 'Português', dir: 'ltr' },
];

export const TRANSLATIONS = {
  en: {
    common: { total: 'Total', gstIncluded: 'GST Included', pricesIncludeGst: 'Prices include GST', language: 'Language', loading: 'Loading…', add: 'Add' },
    cfd: {
      welcome: 'Welcome', table: 'Table',
      pointsEarned: "You'll earn {n} points",
      pointsMissed: 'Sign up to earn {n} points — ask staff to add you!',
    },
    kiosk: { title: 'Self-Service Kiosk', startOrder: 'Start Order', checkout: 'Checkout', orderSent: 'Order sent to kitchen' },
    tableOrder: {
      loadingMenu: 'Loading menu...', tableLabel: 'Table', ordersBtn: 'Orders', backToMenu: 'Back to Menu',
      yourOrder: 'Your Order', cartEmpty: 'Your cart is empty', namePlaceholder: 'Your name (optional)',
      notesPlaceholder: 'Special requests or allergies...', yourOrders: 'Your Orders', noActiveOrders: 'No active orders',
      browseMenu: 'Browse Menu', viewCart: 'View Cart', placeOrder: 'Place Order', placingOrder: 'Placing Order...',
      statusNew: 'Order Received', statusPreparing: 'Preparing', statusReady: 'Ready to Serve', statusServed: 'Served',
      menuLoadFailed: 'Failed to load menu', orderPlaced: 'Order placed!', orderFailed: 'Failed to place order',
    },
    orderOnline: {
      brandTitle: 'NUA · Order Online', subtitle: 'Fresh food, real-time ETA', trackOrder: 'Track an order',
      channelPickup: 'Pickup', channelPickupHint: 'Skip the queue', channelDelivery: 'Delivery', channelDeliveryHint: 'To your door',
      channelDineIn: 'Dine-in', channelDineInHint: 'Order ahead', allCategory: 'All', yourCart: 'Your Cart', prepTime: 'prep',
      emptyCartPrompt: 'Add items to start your order', namePlaceholder: 'Your name *', phonePlaceholder: 'Phone',
      emailPlaceholder: 'Email (optional)', addressPlaceholder: 'Delivery address *', notesPlaceholder: 'Special instructions (e.g. no onion)',
      placeOrderBtn: 'Place order', placing: 'Placing…', paymentCollectedAt: 'Payment collected at {location}',
      pickupWord: 'pickup', deliveryWord: 'delivery', toastNameRequired: 'Name required', toastCartEmpty: 'Cart is empty',
      toastAddressRequired: 'Delivery address required', toastOrderPlaced: 'Order placed!', toastTrackingCode: 'Tracking code: {code}',
      toastFailed: 'Failed',
    },
  },
  it: {
    common: { total: 'Totale', gstIncluded: 'GST Inclusa', pricesIncludeGst: 'Prezzi IVA inclusa', language: 'Lingua', loading: 'Caricamento…', add: 'Aggiungi' },
    cfd: {
      welcome: 'Benvenuto', table: 'Tavolo',
      pointsEarned: 'Guadagnerai {n} punti',
      pointsMissed: 'Iscriviti per guadagnare {n} punti — chiedi al personale di aggiungerti!',
    },
    kiosk: { title: 'Chiosco Self-Service', startOrder: 'Inizia Ordine', checkout: 'Cassa', orderSent: 'Ordine inviato in cucina' },
    tableOrder: {
      loadingMenu: 'Caricamento menu...', tableLabel: 'Tavolo', ordersBtn: 'Ordini', backToMenu: 'Torna al Menu',
      yourOrder: 'Il Tuo Ordine', cartEmpty: 'Il carrello è vuoto', namePlaceholder: 'Il tuo nome (opzionale)',
      notesPlaceholder: 'Richieste speciali o allergie...', yourOrders: 'I Tuoi Ordini', noActiveOrders: 'Nessun ordine attivo',
      browseMenu: 'Sfoglia il Menu', viewCart: 'Vedi Carrello', placeOrder: 'Invia Ordine', placingOrder: 'Invio ordine...',
      statusNew: 'Ordine Ricevuto', statusPreparing: 'In Preparazione', statusReady: 'Pronto da Servire', statusServed: 'Servito',
      menuLoadFailed: 'Impossibile caricare il menu', orderPlaced: 'Ordine inviato!', orderFailed: "Impossibile inviare l'ordine",
    },
    orderOnline: {
      brandTitle: 'NUA · Ordina Online', subtitle: "Cibo fresco, tempi d'attesa in tempo reale", trackOrder: 'Traccia un ordine',
      channelPickup: 'Ritiro', channelPickupHint: 'Salta la fila', channelDelivery: 'Consegna', channelDeliveryHint: 'A casa tua',
      channelDineIn: 'Al Tavolo', channelDineInHint: 'Ordina in anticipo', allCategory: 'Tutti', yourCart: 'Il Tuo Carrello', prepTime: 'preparazione',
      emptyCartPrompt: 'Aggiungi articoli per iniziare il tuo ordine', namePlaceholder: 'Il tuo nome *', phonePlaceholder: 'Telefono',
      emailPlaceholder: 'Email (opzionale)', addressPlaceholder: 'Indirizzo di consegna *', notesPlaceholder: 'Istruzioni speciali (es. senza cipolla)',
      placeOrderBtn: 'Invia ordine', placing: 'Invio in corso…', paymentCollectedAt: 'Pagamento al momento {location}',
      pickupWord: 'del ritiro', deliveryWord: 'della consegna', toastNameRequired: 'Nome obbligatorio', toastCartEmpty: 'Il carrello è vuoto',
      toastAddressRequired: 'Indirizzo di consegna obbligatorio', toastOrderPlaced: 'Ordine inviato!', toastTrackingCode: 'Codice di tracciamento: {code}',
      toastFailed: 'Operazione fallita',
    },
  },
  zh: {
    common: { total: '总计', gstIncluded: '含税', pricesIncludeGst: '价格已含消费税', language: '语言', loading: '加载中…', add: '添加' },
    cfd: {
      welcome: '欢迎光临', table: '桌号',
      pointsEarned: '您将获得 {n} 积分',
      pointsMissed: '注册即可获得 {n} 积分 — 请让服务员为您添加！',
    },
    kiosk: { title: '自助点餐机', startOrder: '开始点餐', checkout: '结账', orderSent: '订单已发送至厨房' },
    tableOrder: {
      loadingMenu: '菜单加载中...', tableLabel: '桌号', ordersBtn: '订单', backToMenu: '返回菜单',
      yourOrder: '您的订单', cartEmpty: '购物车是空的', namePlaceholder: '您的姓名（可选）',
      notesPlaceholder: '特殊要求或过敏信息...', yourOrders: '您的订单', noActiveOrders: '暂无进行中的订单',
      browseMenu: '浏览菜单', viewCart: '查看购物车', placeOrder: '下单', placingOrder: '正在下单...',
      statusNew: '订单已收到', statusPreparing: '制作中', statusReady: '可以上菜', statusServed: '已上菜',
      menuLoadFailed: '菜单加载失败', orderPlaced: '下单成功！', orderFailed: '下单失败',
    },
    orderOnline: {
      brandTitle: 'NUA · 在线点餐', subtitle: '新鲜美食，实时预计时间', trackOrder: '查询订单',
      channelPickup: '自取', channelPickupHint: '免排队', channelDelivery: '外送', channelDeliveryHint: '送到家门口',
      channelDineIn: '堂食', channelDineInHint: '提前点餐', allCategory: '全部', yourCart: '您的购物车', prepTime: '制作时间',
      emptyCartPrompt: '添加菜品以开始下单', namePlaceholder: '您的姓名 *', phonePlaceholder: '电话',
      emailPlaceholder: '邮箱（可选）', addressPlaceholder: '送货地址 *', notesPlaceholder: '特殊要求（例如不要洋葱）',
      placeOrderBtn: '下单', placing: '下单中…', paymentCollectedAt: '{location}时付款',
      pickupWord: '自取', deliveryWord: '送达', toastNameRequired: '请填写姓名', toastCartEmpty: '购物车是空的',
      toastAddressRequired: '请填写送货地址', toastOrderPlaced: '下单成功！', toastTrackingCode: '追踪码：{code}',
      toastFailed: '操作失败',
    },
  },
  hi: {
    common: { total: 'कुल', gstIncluded: 'जीएसटी शामिल', pricesIncludeGst: 'कीमतों में जीएसटी शामिल है', language: 'भाषा', loading: 'लोड हो रहा है…', add: 'जोड़ें' },
    cfd: {
      welcome: 'स्वागत है', table: 'टेबल',
      pointsEarned: 'आपको {n} पॉइंट्स मिलेंगे',
      pointsMissed: '{n} पॉइंट्स कमाने के लिए साइन अप करें — स्टाफ़ से जोड़ने को कहें!',
    },
    kiosk: { title: 'सेल्फ़-सर्विस कियोस्क', startOrder: 'ऑर्डर शुरू करें', checkout: 'चेकआउट', orderSent: 'ऑर्डर रसोई में भेज दिया गया' },
    tableOrder: {
      loadingMenu: 'मेनू लोड हो रहा है...', tableLabel: 'टेबल', ordersBtn: 'ऑर्डर', backToMenu: 'मेनू पर वापस जाएं',
      yourOrder: 'आपका ऑर्डर', cartEmpty: 'आपकी कार्ट खाली है', namePlaceholder: 'आपका नाम (वैकल्पिक)',
      notesPlaceholder: 'विशेष अनुरोध या एलर्जी...', yourOrders: 'आपके ऑर्डर', noActiveOrders: 'कोई सक्रिय ऑर्डर नहीं',
      browseMenu: 'मेनू देखें', viewCart: 'कार्ट देखें', placeOrder: 'ऑर्डर करें', placingOrder: 'ऑर्डर किया जा रहा है...',
      statusNew: 'ऑर्डर मिल गया', statusPreparing: 'तैयार हो रहा है', statusReady: 'परोसने के लिए तैयार', statusServed: 'परोसा गया',
      menuLoadFailed: 'मेनू लोड नहीं हो सका', orderPlaced: 'ऑर्डर हो गया!', orderFailed: 'ऑर्डर देने में विफल',
    },
    orderOnline: {
      brandTitle: 'NUA · ऑनलाइन ऑर्डर करें', subtitle: 'ताज़ा खाना, रीयल-टाइम समय अनुमान', trackOrder: 'ऑर्डर ट्रैक करें',
      channelPickup: 'पिकअप', channelPickupHint: 'लाइन छोड़ें', channelDelivery: 'डिलीवरी', channelDeliveryHint: 'आपके दरवाज़े तक',
      channelDineIn: 'डाइन-इन', channelDineInHint: 'पहले से ऑर्डर करें', allCategory: 'सभी', yourCart: 'आपकी कार्ट', prepTime: 'तैयारी',
      emptyCartPrompt: 'ऑर्डर शुरू करने के लिए आइटम जोड़ें', namePlaceholder: 'आपका नाम *', phonePlaceholder: 'फ़ोन',
      emailPlaceholder: 'ईमेल (वैकल्पिक)', addressPlaceholder: 'डिलीवरी पता *', notesPlaceholder: 'विशेष निर्देश (जैसे बिना प्याज़)',
      placeOrderBtn: 'ऑर्डर करें', placing: 'ऑर्डर हो रहा है…', paymentCollectedAt: '{location} पर भुगतान लिया जाएगा',
      pickupWord: 'पिकअप', deliveryWord: 'डिलीवरी', toastNameRequired: 'नाम आवश्यक है', toastCartEmpty: 'कार्ट खाली है',
      toastAddressRequired: 'डिलीवरी पता आवश्यक है', toastOrderPlaced: 'ऑर्डर हो गया!', toastTrackingCode: 'ट्रैकिंग कोड: {code}',
      toastFailed: 'विफल',
    },
  },
  es: {
    common: { total: 'Total', gstIncluded: 'IVA Incluido', pricesIncludeGst: 'Precios con IVA incluido', language: 'Idioma', loading: 'Cargando…', add: 'Añadir' },
    cfd: {
      welcome: 'Bienvenido', table: 'Mesa',
      pointsEarned: 'Ganarás {n} puntos',
      pointsMissed: 'Regístrate para ganar {n} puntos — ¡pide al personal que te agregue!',
    },
    kiosk: { title: 'Quiosco de Autoservicio', startOrder: 'Iniciar Pedido', checkout: 'Pagar', orderSent: 'Pedido enviado a la cocina' },
    tableOrder: {
      loadingMenu: 'Cargando menú...', tableLabel: 'Mesa', ordersBtn: 'Pedidos', backToMenu: 'Volver al Menú',
      yourOrder: 'Tu Pedido', cartEmpty: 'Tu carrito está vacío', namePlaceholder: 'Tu nombre (opcional)',
      notesPlaceholder: 'Peticiones especiales o alergias...', yourOrders: 'Tus Pedidos', noActiveOrders: 'No hay pedidos activos',
      browseMenu: 'Ver Menú', viewCart: 'Ver Carrito', placeOrder: 'Realizar Pedido', placingOrder: 'Enviando pedido...',
      statusNew: 'Pedido Recibido', statusPreparing: 'En Preparación', statusReady: 'Listo para Servir', statusServed: 'Servido',
      menuLoadFailed: 'Error al cargar el menú', orderPlaced: '¡Pedido realizado!', orderFailed: 'No se pudo realizar el pedido',
    },
    orderOnline: {
      brandTitle: 'NUA · Pedir en Línea', subtitle: 'Comida fresca, tiempo de espera en tiempo real', trackOrder: 'Rastrear un pedido',
      channelPickup: 'Recoger', channelPickupHint: 'Sin hacer fila', channelDelivery: 'Entrega', channelDeliveryHint: 'Hasta tu puerta',
      channelDineIn: 'Comer Aquí', channelDineInHint: 'Pide con anticipación', allCategory: 'Todos', yourCart: 'Tu Carrito', prepTime: 'preparación',
      emptyCartPrompt: 'Agrega artículos para empezar tu pedido', namePlaceholder: 'Tu nombre *', phonePlaceholder: 'Teléfono',
      emailPlaceholder: 'Correo electrónico (opcional)', addressPlaceholder: 'Dirección de entrega *', notesPlaceholder: 'Instrucciones especiales (ej. sin cebolla)',
      placeOrderBtn: 'Realizar pedido', placing: 'Enviando…', paymentCollectedAt: 'Pago al momento de la {location}',
      pickupWord: 'recogida', deliveryWord: 'entrega', toastNameRequired: 'Nombre obligatorio', toastCartEmpty: 'El carrito está vacío',
      toastAddressRequired: 'Dirección de entrega obligatoria', toastOrderPlaced: '¡Pedido realizado!', toastTrackingCode: 'Código de seguimiento: {code}',
      toastFailed: 'Error',
    },
  },
  vi: {
    common: { total: 'Tổng cộng', gstIncluded: 'Đã bao gồm thuế', pricesIncludeGst: 'Giá đã bao gồm thuế GST', language: 'Ngôn ngữ', loading: 'Đang tải…', add: 'Thêm' },
    cfd: {
      welcome: 'Xin chào', table: 'Bàn',
      pointsEarned: 'Bạn sẽ nhận được {n} điểm',
      pointsMissed: 'Đăng ký để nhận {n} điểm — hãy nhờ nhân viên thêm bạn!',
    },
    kiosk: { title: 'Ki-ốt Tự Phục Vụ', startOrder: 'Bắt Đầu Đặt Hàng', checkout: 'Thanh Toán', orderSent: 'Đơn hàng đã được gửi đến bếp' },
    tableOrder: {
      loadingMenu: 'Đang tải thực đơn...', tableLabel: 'Bàn', ordersBtn: 'Đơn hàng', backToMenu: 'Quay Lại Thực Đơn',
      yourOrder: 'Đơn Hàng Của Bạn', cartEmpty: 'Giỏ hàng của bạn đang trống', namePlaceholder: 'Tên của bạn (không bắt buộc)',
      notesPlaceholder: 'Yêu cầu đặc biệt hoặc dị ứng...', yourOrders: 'Đơn Hàng Của Bạn', noActiveOrders: 'Không có đơn hàng nào đang xử lý',
      browseMenu: 'Xem Thực Đơn', viewCart: 'Xem Giỏ Hàng', placeOrder: 'Đặt Hàng', placingOrder: 'Đang đặt hàng...',
      statusNew: 'Đã Nhận Đơn', statusPreparing: 'Đang Chuẩn Bị', statusReady: 'Sẵn Sàng Phục Vụ', statusServed: 'Đã Phục Vụ',
      menuLoadFailed: 'Không thể tải thực đơn', orderPlaced: 'Đặt hàng thành công!', orderFailed: 'Đặt hàng không thành công',
    },
    orderOnline: {
      brandTitle: 'NUA · Đặt Hàng Trực Tuyến', subtitle: 'Đồ ăn tươi ngon, thời gian ước tính theo thời gian thực', trackOrder: 'Theo dõi đơn hàng',
      channelPickup: 'Tự đến lấy', channelPickupHint: 'Không cần xếp hàng', channelDelivery: 'Giao hàng', channelDeliveryHint: 'Đến tận cửa nhà bạn',
      channelDineIn: 'Dùng tại chỗ', channelDineInHint: 'Đặt trước', allCategory: 'Tất cả', yourCart: 'Giỏ Hàng Của Bạn', prepTime: 'chuẩn bị',
      emptyCartPrompt: 'Thêm món để bắt đầu đặt hàng', namePlaceholder: 'Tên của bạn *', phonePlaceholder: 'Số điện thoại',
      emailPlaceholder: 'Email (không bắt buộc)', addressPlaceholder: 'Địa chỉ giao hàng *', notesPlaceholder: 'Yêu cầu đặc biệt (vd. không hành)',
      placeOrderBtn: 'Đặt hàng', placing: 'Đang xử lý…', paymentCollectedAt: 'Thanh toán khi {location}',
      pickupWord: 'nhận hàng', deliveryWord: 'giao hàng', toastNameRequired: 'Vui lòng nhập tên', toastCartEmpty: 'Giỏ hàng đang trống',
      toastAddressRequired: 'Vui lòng nhập địa chỉ giao hàng', toastOrderPlaced: 'Đặt hàng thành công!', toastTrackingCode: 'Mã theo dõi: {code}',
      toastFailed: 'Thất bại',
    },
  },
  ar: {
    common: { total: 'الإجمالي', gstIncluded: 'شامل الضريبة', pricesIncludeGst: 'الأسعار شاملة الضريبة', language: 'اللغة', loading: 'جارٍ التحميل…', add: 'إضافة' },
    cfd: {
      welcome: 'أهلاً وسهلاً', table: 'طاولة',
      pointsEarned: 'ستحصل على {n} نقطة',
      pointsMissed: 'سجّل لتحصل على {n} نقطة — اطلب من الموظف إضافتك!',
    },
    kiosk: { title: 'كشك الخدمة الذاتية', startOrder: 'ابدأ الطلب', checkout: 'الدفع', orderSent: 'تم إرسال الطلب إلى المطبخ' },
    tableOrder: {
      loadingMenu: 'جارٍ تحميل القائمة...', tableLabel: 'طاولة', ordersBtn: 'الطلبات', backToMenu: 'العودة إلى القائمة',
      yourOrder: 'طلبك', cartEmpty: 'سلة التسوق فارغة', namePlaceholder: 'اسمك (اختياري)',
      notesPlaceholder: 'طلبات خاصة أو حساسية...', yourOrders: 'طلباتك', noActiveOrders: 'لا توجد طلبات نشطة',
      browseMenu: 'تصفح القائمة', viewCart: 'عرض السلة', placeOrder: 'إرسال الطلب', placingOrder: 'جارٍ إرسال الطلب...',
      statusNew: 'تم استلام الطلب', statusPreparing: 'قيد التحضير', statusReady: 'جاهز للتقديم', statusServed: 'تم التقديم',
      menuLoadFailed: 'فشل تحميل القائمة', orderPlaced: 'تم إرسال الطلب!', orderFailed: 'فشل إرسال الطلب',
    },
    orderOnline: {
      brandTitle: 'NUA · اطلب أونلاين', subtitle: 'طعام طازج، وقت انتظار فوري', trackOrder: 'تتبع الطلب',
      channelPickup: 'استلام', channelPickupHint: 'تخطَّ الطابور', channelDelivery: 'توصيل', channelDeliveryHint: 'حتى باب منزلك',
      channelDineIn: 'تناول في المطعم', channelDineInHint: 'اطلب مسبقًا', allCategory: 'الكل', yourCart: 'سلتك', prepTime: 'التحضير',
      emptyCartPrompt: 'أضف عناصر لبدء طلبك', namePlaceholder: 'اسمك *', phonePlaceholder: 'رقم الهاتف',
      emailPlaceholder: 'البريد الإلكتروني (اختياري)', addressPlaceholder: 'عنوان التوصيل *', notesPlaceholder: 'تعليمات خاصة (مثال: بدون بصل)',
      placeOrderBtn: 'إرسال الطلب', placing: 'جارٍ الإرسال…', paymentCollectedAt: 'يتم الدفع عند {location}',
      pickupWord: 'الاستلام', deliveryWord: 'التوصيل', toastNameRequired: 'الاسم مطلوب', toastCartEmpty: 'السلة فارغة',
      toastAddressRequired: 'عنوان التوصيل مطلوب', toastOrderPlaced: 'تم إرسال الطلب!', toastTrackingCode: 'رمز التتبع: {code}',
      toastFailed: 'فشل',
    },
  },
  pt: {
    common: { total: 'Total', gstIncluded: 'Imposto Incluído', pricesIncludeGst: 'Preços com imposto incluído', language: 'Idioma', loading: 'Carregando…', add: 'Adicionar' },
    cfd: {
      welcome: 'Bem-vindo', table: 'Mesa',
      pointsEarned: 'Você ganhará {n} pontos',
      pointsMissed: 'Cadastre-se para ganhar {n} pontos — peça à equipe para adicionar você!',
    },
    kiosk: { title: 'Quiosque de Autoatendimento', startOrder: 'Iniciar Pedido', checkout: 'Finalizar', orderSent: 'Pedido enviado à cozinha' },
    tableOrder: {
      loadingMenu: 'Carregando cardápio...', tableLabel: 'Mesa', ordersBtn: 'Pedidos', backToMenu: 'Voltar ao Cardápio',
      yourOrder: 'Seu Pedido', cartEmpty: 'Seu carrinho está vazio', namePlaceholder: 'Seu nome (opcional)',
      notesPlaceholder: 'Pedidos especiais ou alergias...', yourOrders: 'Seus Pedidos', noActiveOrders: 'Nenhum pedido ativo',
      browseMenu: 'Ver Cardápio', viewCart: 'Ver Carrinho', placeOrder: 'Fazer Pedido', placingOrder: 'Enviando pedido...',
      statusNew: 'Pedido Recebido', statusPreparing: 'Em Preparo', statusReady: 'Pronto para Servir', statusServed: 'Servido',
      menuLoadFailed: 'Falha ao carregar o cardápio', orderPlaced: 'Pedido enviado!', orderFailed: 'Falha ao enviar o pedido',
    },
    orderOnline: {
      brandTitle: 'NUA · Peça Online', subtitle: 'Comida fresca, tempo estimado em tempo real', trackOrder: 'Rastrear um pedido',
      channelPickup: 'Retirada', channelPickupHint: 'Sem filas', channelDelivery: 'Entrega', channelDeliveryHint: 'Até a sua porta',
      channelDineIn: 'Comer no Local', channelDineInHint: 'Peça com antecedência', allCategory: 'Todos', yourCart: 'Seu Carrinho', prepTime: 'preparo',
      emptyCartPrompt: 'Adicione itens para começar seu pedido', namePlaceholder: 'Seu nome *', phonePlaceholder: 'Telefone',
      emailPlaceholder: 'E-mail (opcional)', addressPlaceholder: 'Endereço de entrega *', notesPlaceholder: 'Instruções especiais (ex.: sem cebola)',
      placeOrderBtn: 'Fazer pedido', placing: 'Enviando…', paymentCollectedAt: 'Pagamento no momento da {location}',
      pickupWord: 'retirada', deliveryWord: 'entrega', toastNameRequired: 'Nome obrigatório', toastCartEmpty: 'O carrinho está vazio',
      toastAddressRequired: 'Endereço de entrega obrigatório', toastOrderPlaced: 'Pedido enviado!', toastTrackingCode: 'Código de rastreamento: {code}',
      toastFailed: 'Falha',
    },
  },
};

export function translate(lang, key, vars) {
  const [section, sub] = key.split('.');
  const dict = TRANSLATIONS[lang] || TRANSLATIONS.en;
  let str = dict?.[section]?.[sub] ?? TRANSLATIONS.en?.[section]?.[sub] ?? key;
  if (vars) {
    Object.entries(vars).forEach(([k, v]) => { str = str.replace(`{${k}}`, v); });
  }
  return str;
}
