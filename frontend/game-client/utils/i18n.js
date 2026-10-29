import { ref } from 'vue'

export const LANGS = [
	{ code: 'zh-Hans', name: '简体中文' },
	{ code: 'zh-Hant', name: '繁體中文' },
	{ code: 'en', name: 'English' },
	{ code: 'ja', name: '日本語' },
	{ code: 'ko', name: '한국어' },
	{ code: 'es', name: 'Español' },
	{ code: 'fr', name: 'Français' },
	{ code: 'de', name: 'Deutsch' },
	{ code: 'pt', name: 'Português' },
	{ code: 'ru', name: 'Русский' },
	{ code: 'ar', name: 'العربية' },
	{ code: 'th', name: 'ไทย' },
	{ code: 'vi', name: 'Tiếng Việt' },
	{ code: 'id', name: 'Bahasa Indonesia' },
	{ code: 'it', name: 'Italiano' },
	{ code: 'tr', name: 'Türkçe' },
	{ code: 'pl', name: 'Polski' },
	{ code: 'nl', name: 'Nederlands' },
	{ code: 'hi', name: 'हिन्दी' },
	{ code: 'ms', name: 'Bahasa Melayu' },
	{ code: 'fil', name: 'Filipino' },
	{ code: 'sv', name: 'Svenska' }
]

const zh = {
	saving_assets: '正在把这一段的图片和音频保存到本地',
	retry: '重试',
	view: '查看',
	close: '关闭',
	choose_login: '选择登录方式',
	device_login: '快速登录',
	signing_in: '正在登录',
	google_login: '使用 Google 登录',
	uid_copied: 'UID 已复制',
	uid_empty: '登录后才能复制 UID',
	continue_game: '继续游戏',
	menu_continue: '继续',
	menu_archives: '存档',
	menu_stories: '故事',
	menu_restart: '从头开始',
	menu_quit: '退出',
	start_game: '开始游戏',
	saves: '历史存档',
	gallery: '故事解锁',
	restart_story: '从头开始',
	logout: '退出',
	connecting: '正在连接故事',
	landscape: '横屏',
	portrait: '竖屏',
	checking: '正在检查资源',
	assets_progress: '资源 {done} / {total}',
	missing_game_id: '请先在 config/game.js 填写后台的游戏 ID',
	story_unavailable: '故事还没发布，或游戏 ID 还没在后台配好',
	login_failed: '登录失败',
	google_missing: '请先配置 Google 客户端 ID',
	google_browser: 'Google 登录请用浏览器打开',
	google_ok: 'Google 登录成功',
	google_failed: 'Google 登录失败',
	google_script: 'Google 登录脚本加载失败',
	no_story: '这部故事还没有可播放的剧情',
	download_failed_net: '资源下载失败，请检查网络后重试',
	back: '返回',
	record: '记录',
	save: '存档',
	screen: '画面',
	sound: '声音',
	off: '关',
	on: '开',
	skip: '点击跳过',
	choose: '请选择',
	make_choice: '做出你的选择',
	tap: '点击继续',
	start_over: '重新开始',
	back_title: '回到标题',
	new_segment: '正在加载这一章',
	assets_incomplete: '资源没有下完',
	ending: '结局',
	checking_segment: '正在检查这一段的资源',
	to_be_continued: '未完待续',
	unlocked_new: '解锁了新内容',
	saved_history: '已写入历史存档',
	added_gallery: '已放入故事解锁',
	videos: '视频',
	portraits: '立绘',
	locked: '未解锁',
	empty_gallery: '这一栏还没有内容。',
	gallery_failed: '解锁列表读取失败',
	not_unlocked: '还没有解锁',
	save_hint: '点一条就能从那里继续。自动存档会跟着剧情走，手动存档在播放时写入。',
	auto_save: '自动存档',
	manual_save: '手动存档',
	untitled: '未命名',
	load: '读取',
	delete: '删除',
	no_saves: '还没有存档。开始游戏后会留下自动存档。',
	saves_failed: '存档读取失败',
	save_missing: '这条存档对应的剧情已经不在了',
	delete_failed: '删除失败',
	request_failed: '请求失败',
	network_error: '当前网络异常，请重新连接',
	download_failed: '下载失败',
	language: '语言',
	app_name: '星河剧场'
}

const en = {
	saving_assets: 'Saving this chapter’s images and audio on this device',
	retry: 'Retry',
	view: 'View',
	close: 'Close',
	choose_login: 'Choose how to sign in',
	device_login: 'QUICK SIGN-IN',
	signing_in: 'SIGNING IN',
	google_login: 'SIGN IN WITH GOOGLE',
	uid_copied: 'UID copied',
	uid_empty: 'Sign in before copying the UID',
	continue_game: 'Continue',
	menu_continue: 'CONTINUE',
	menu_archives: 'ARCHIVES',
	menu_stories: 'STORIES',
	menu_restart: 'START FROM BEGINNING',
	menu_quit: 'QUIT',
	start_game: 'Start',
	saves: 'Saves',
	gallery: 'Unlocks',
	restart_story: 'Start over',
	logout: 'Sign out',
	connecting: 'Connecting to the story',
	landscape: 'Landscape',
	portrait: 'Portrait',
	checking: 'Checking files',
	assets_progress: 'Files {done} / {total}',
	missing_game_id: 'Set the game ID in config/game.js first',
	story_unavailable: 'This story is not published, or the game ID is not set',
	login_failed: 'Sign-in failed',
	google_missing: 'Set the Google client ID first',
	google_browser: 'Open Google sign-in in a browser',
	google_ok: 'Signed in with Google',
	google_failed: 'Google sign-in failed',
	google_script: 'Could not load Google sign-in',
	no_story: 'This story has no scenes to play yet',
	download_failed_net: 'Download failed. Check the network and retry',
	back: 'Back',
	record: 'Log',
	save: 'Save',
	screen: 'Screen',
	sound: 'Sound',
	off: 'Off',
	on: 'On',
	skip: 'Tap to skip',
	choose: 'Choose',
	make_choice: 'MAKE YOUR CHOICE',
	tap: 'Tap to continue',
	start_over: 'Restart',
	back_title: 'Title',
	new_segment: 'Loading the next chapter',
	assets_incomplete: 'Files did not finish downloading',
	ending: 'Ending',
	checking_segment: 'Checking this chapter',
	to_be_continued: 'To be continued',
	unlocked_new: 'New unlock',
	saved_history: 'Saved to history',
	added_gallery: 'Added to unlocks',
	videos: 'Videos',
	portraits: 'Portraits',
	locked: 'Locked',
	empty_gallery: 'Nothing in this tab yet.',
	gallery_failed: 'Could not load unlocks',
	not_unlocked: 'Not unlocked yet',
	save_hint: 'Tap a save to continue. Auto saves follow the story. Manual saves are written while you play.',
	auto_save: 'Auto save',
	manual_save: 'Manual save',
	untitled: 'Untitled',
	load: 'Load',
	delete: 'Delete',
	no_saves: 'No saves yet. An auto save appears after you start.',
	saves_failed: 'Could not load saves',
	save_missing: 'The scene for this save is gone',
	delete_failed: 'Could not delete',
	request_failed: 'Request failed',
	network_error: 'Network error. Please reconnect.',
	download_failed: 'Download failed',
	language: 'Language',
	app_name: 'Galaxy Theatre'
}

function pack(partial) {
	return Object.assign({}, en, partial)
}

const PACKS = {
	'zh-Hans': zh,
	'zh-Hant': pack({
		saving_assets: '正在把這一段的圖片和音訊存到本機',
		retry: '重試',
		view: '查看',
		close: '關閉',
		choose_login: '選擇登入方式',
		device_login: '快速登入',
		google_login: '使用 Google 登入',
		uid_copied: 'UID 已複製',
		uid_empty: '登入後才能複製 UID',
		continue_game: '繼續遊戲',
		menu_continue: '繼續',
		menu_archives: '存檔',
		menu_stories: '故事',
		menu_restart: '從頭開始',
		menu_quit: '退出',
		start_game: '開始遊戲',
		saves: '歷史存檔',
		gallery: '故事解鎖',
		restart_story: '從頭開始',
		logout: '登出',
		connecting: '正在連接故事',
		landscape: '橫屏',
		portrait: '豎屏',
		checking: '正在檢查資源',
		assets_progress: '資源 {done} / {total}',
		login_failed: '登入失敗',
		back: '返回',
		save: '存檔',
		screen: '畫面',
		sound: '聲音',
		off: '關',
		on: '開',
		skip: '點擊跳過',
		choose: '請選擇',
		make_choice: '做出你的選擇',
		tap: '點擊繼續',
		start_over: '重新開始',
		back_title: '回到標題',
		ending: '結局',
		videos: '影片',
		portraits: '立繪',
		locked: '未解鎖',
		load: '讀取',
		delete: '刪除',
		network_error: '當前網路異常，請重新連接',
		language: '語言',
		app_name: '星河劇場'
	}),
	en,
	ja: pack({
		retry: '再試行', view: '見る', close: '閉じる', choose_login: 'ログイン方法',
		device_login: 'デバイスですぐログイン', google_login: 'Google ログイン',
		continue_game: 'つづきから', start_game: '開始', saves: 'セーブ', gallery: '解放リスト',
		restart_story: '最初から', logout: 'ログアウト', connecting: '物語に接続しています',
		landscape: '横画面', portrait: '縦画面', checking: 'ファイルを確認しています',
		assets_progress: 'ファイル {done} / {total}', back: '戻る', save: 'セーブ',
		screen: '画面', sound: '音声', off: 'オフ', on: 'オン', skip: 'タップでスキップ',
		choose: '選択してください', tap: 'タップして進む', start_over: '最初から',
		back_title: 'タイトルへ', ending: '結末', videos: '動画', portraits: '立ち絵',
		locked: '未解放', load: '読み込む', delete: '削除', language: '言語',
		login_failed: 'ログインに失敗しました', new_segment: '次の章を読み込んでいます',
		to_be_continued: 'つづく', unlocked_new: '新しい解放', saved_history: '履歴に保存しました',
		network_error: 'ネットワーク異常です。再接続してください',
		app_name: '銀河劇場'
	}),
	ko: pack({
		retry: '다시 시도', view: '보기', close: '닫기', choose_login: '로그인 방식',
		device_login: '기기로 빠른 로그인', google_login: 'Google 로그인',
		continue_game: '이어하기', start_game: '시작', saves: '저장', gallery: '잠금 해제',
		restart_story: '처음부터', logout: '로그아웃', connecting: '스토리에 연결하는 중',
		landscape: '가로', portrait: '세로', checking: '파일을 확인하는 중',
		assets_progress: '파일 {done} / {total}', back: '뒤로', save: '저장',
		screen: '화면', sound: '소리', off: '끔', on: '켬', skip: '탭하여 건너뛰기',
		choose: '선택하세요', tap: '탭하여 계속', start_over: '다시 시작',
		back_title: '타이틀로', ending: '엔딩', videos: '영상', portraits: '일러스트',
		locked: '잠김', load: '불러오기', delete: '삭제', language: '언어',
		login_failed: '로그인에 실패했습니다',
		network_error: '네트워크 오류입니다. 다시 연결해 주세요',
		app_name: '은하극장'
	}),
	es: pack({
		retry: 'Reintentar', view: 'Ver', close: 'Cerrar', choose_login: 'Cómo entrar',
		device_login: 'Entrar con el dispositivo', google_login: 'Entrar con Google',
		continue_game: 'Continuar', start_game: 'Empezar', saves: 'Partidas', gallery: 'Desbloqueos',
		restart_story: 'Desde el inicio', logout: 'Salir', landscape: 'Horizontal', portrait: 'Vertical',
		back: 'Volver', save: 'Guardar', screen: 'Pantalla', sound: 'Sonido', off: 'No', on: 'Sí',
		skip: 'Toca para saltar', choose: 'Elige', tap: 'Toca para seguir', start_over: 'Reiniciar',
		back_title: 'Título', ending: 'Final', videos: 'Vídeos', portraits: 'Retratos',
		locked: 'Bloqueado', load: 'Cargar', delete: 'Eliminar', language: 'Idioma',
		network_error: 'Error de red. Vuelve a conectarte.',
		app_name: 'Teatro Galaxia'
	}),
	fr: pack({
		retry: 'Réessayer', view: 'Voir', close: 'Fermer', device_login: 'Connexion appareil',
		google_login: 'Connexion Google', continue_game: 'Continuer', start_game: 'Commencer',
		saves: 'Sauvegardes', gallery: 'Déblocages', logout: 'Quitter', landscape: 'Paysage',
		portrait: 'Portrait', back: 'Retour', save: 'Sauver', screen: 'Écran', sound: 'Son',
		off: 'Non', on: 'Oui', choose: 'Choisir', tap: 'Touchez pour continuer',
		start_over: 'Recommencer', ending: 'Fin', videos: 'Vidéos', portraits: 'Portraits',
		locked: 'Verrouillé', load: 'Charger', delete: 'Supprimer', language: 'Langue',
		network_error: 'Réseau instable. Veuillez vous reconnecter.',
		app_name: 'Théâtre Galaxie'
	}),
	de: pack({
		retry: 'Erneut', view: 'Ansehen', close: 'Schließen', device_login: 'Mit Gerät anmelden',
		google_login: 'Mit Google anmelden', continue_game: 'Weiter', start_game: 'Start',
		saves: 'Speicherstände', gallery: 'Freigeschaltet', logout: 'Abmelden',
		landscape: 'Quer', portrait: 'Hoch', back: 'Zurück', save: 'Speichern',
		screen: 'Bild', sound: 'Ton', off: 'Aus', on: 'An', choose: 'Wählen',
		tap: 'Tippen zum Weiter', start_over: 'Neustart', ending: 'Ende',
		videos: 'Videos', portraits: 'Porträts', locked: 'Gesperrt', load: 'Laden',
		delete: 'Löschen', language: 'Sprache',
		network_error: 'Netzwerkfehler. Bitte erneut verbinden.',
		app_name: 'Galaxie-Theater'
	}),
	pt: pack({
		retry: 'Tentar de novo', view: 'Ver', close: 'Fechar', device_login: 'Entrar pelo aparelho',
		google_login: 'Entrar com Google', continue_game: 'Continuar', start_game: 'Começar',
		saves: 'Salvos', gallery: 'Desbloqueios', logout: 'Sair', landscape: 'Paisagem',
		portrait: 'Retrato', back: 'Voltar', save: 'Salvar', screen: 'Tela', sound: 'Som',
		off: 'Não', on: 'Sim', choose: 'Escolha', tap: 'Toque para continuar',
		start_over: 'Reiniciar', ending: 'Final', videos: 'Vídeos', portraits: 'Retratos',
		locked: 'Bloqueado', load: 'Carregar', delete: 'Excluir', language: 'Idioma',
		network_error: 'Erro de rede. Ligue-se novamente.',
		app_name: 'Teatro Galáxia'
	}),
	ru: pack({
		retry: 'Ещё раз', view: 'Открыть', close: 'Закрыть', device_login: 'Вход с устройства',
		google_login: 'Вход через Google', continue_game: 'Продолжить', start_game: 'Начать',
		saves: 'Сохранения', gallery: 'Открытое', logout: 'Выйти', landscape: 'Альбом',
		portrait: 'Портрет', back: 'Назад', save: 'Сохранить', screen: 'Экран', sound: 'Звук',
		off: 'Выкл', on: 'Вкл', choose: 'Выберите', tap: 'Нажмите, чтобы продолжить',
		start_over: 'Заново', ending: 'Конец', videos: 'Видео', portraits: 'Портреты',
		locked: 'Закрыто', load: 'Загрузить', delete: 'Удалить', language: 'Язык',
		network_error: 'Ошибка сети. Подключитесь снова.',
		app_name: 'Театр «Галактика»'
	}),
	ar: pack({
		retry: 'إعادة', view: 'عرض', close: 'إغلاق', device_login: 'دخول بالجهاز',
		google_login: 'دخول Google', continue_game: 'متابعة', start_game: 'ابدأ',
		saves: 'الحفظ', gallery: 'المفتوح', logout: 'خروج', landscape: 'أفقي', portrait: 'عمودي',
		back: 'رجوع', save: 'حفظ', screen: 'الشاشة', sound: 'الصوت', off: 'إيقاف', on: 'تشغيل',
		choose: 'اختر', tap: 'المتابعة', start_over: 'من جديد', ending: 'النهاية',
		videos: 'فيديو', portraits: 'صور', locked: 'مقفل', load: 'تحميل', delete: 'حذف', language: 'اللغة',
		network_error: 'الشبكة غير مستقرة. أعد الاتصال.',
		app_name: 'مسرح المجرة'
	}),
	th: pack({
		retry: 'ลองใหม่', view: 'ดู', close: 'ปิด', device_login: 'เข้าด้วยอุปกรณ์',
		google_login: 'เข้าด้วย Google', continue_game: 'เล่นต่อ', start_game: 'เริ่ม',
		saves: 'เซฟ', gallery: 'ปลดล็อก', logout: 'ออก', landscape: 'แนวนอน', portrait: 'แนวตั้ง',
		back: 'กลับ', save: 'เซฟ', screen: 'จอ', sound: 'เสียง', off: 'ปิด', on: 'เปิด',
		choose: 'เลือก', tap: 'แตะเพื่อไปต่อ', start_over: 'เริ่มใหม่', ending: 'จบ',
		videos: 'วิดีโอ', portraits: 'ภาพ', locked: 'ยังล็อก', load: 'โหลด', delete: 'ลบ', language: 'ภาษา',
		network_error: 'เครือข่ายผิดปกติ กรุณาเชื่อมต่อใหม่',
		app_name: 'โรงละครกาแล็กซี'
	}),
	vi: pack({
		retry: 'Thử lại', view: 'Xem', close: 'Đóng', device_login: 'Đăng nhập bằng thiết bị',
		google_login: 'Đăng nhập Google', continue_game: 'Tiếp tục', start_game: 'Bắt đầu',
		saves: 'Lưu', gallery: 'Mở khóa', logout: 'Thoát', landscape: 'Ngang', portrait: 'Dọc',
		back: 'Quay lại', save: 'Lưu', screen: 'Màn hình', sound: 'Âm thanh', off: 'Tắt', on: 'Bật',
		choose: 'Chọn', tap: 'Chạm để tiếp', start_over: 'Chơi lại', ending: 'Kết',
		videos: 'Video', portraits: 'Ảnh', locked: 'Chưa mở', load: 'Tải', delete: 'Xóa', language: 'Ngôn ngữ',
		network_error: 'Mạng đang lỗi. Hãy kết nối lại.',
		app_name: 'Nhà hát Ngân Hà'
	}),
	id: pack({
		retry: 'Coba lagi', view: 'Lihat', close: 'Tutup', device_login: 'Masuk dengan perangkat',
		google_login: 'Masuk Google', continue_game: 'Lanjut', start_game: 'Mulai',
		saves: 'Simpanan', gallery: 'Terbuka', logout: 'Keluar', landscape: 'Mendatar', portrait: 'Tegak',
		back: 'Kembali', save: 'Simpan', screen: 'Layar', sound: 'Suara', off: 'Mati', on: 'Nyala',
		choose: 'Pilih', tap: 'Ketuk untuk lanjut', start_over: 'Ulang', ending: 'Akhir',
		videos: 'Video', portraits: 'Potret', locked: 'Terkunci', load: 'Muat', delete: 'Hapus', language: 'Bahasa',
		network_error: 'Jaringan bermasalah. Sambungkan kembali.',
		app_name: 'Teater Galaksi'
	}),
	it: pack({
		retry: 'Riprova', view: 'Vedi', close: 'Chiudi', device_login: 'Accesso dal dispositivo',
		google_login: 'Accesso Google', continue_game: 'Continua', start_game: 'Inizia',
		saves: 'Salvataggi', gallery: 'Sblocchi', logout: 'Esci', landscape: 'Orizzontale', portrait: 'Verticale',
		back: 'Indietro', save: 'Salva', screen: 'Schermo', sound: 'Audio', off: 'No', on: 'Sì',
		choose: 'Scegli', tap: 'Tocca per continuare', start_over: 'Ricomincia', ending: 'Finale',
		videos: 'Video', portraits: 'Ritratti', locked: 'Bloccato', load: 'Carica', delete: 'Elimina', language: 'Lingua',
		network_error: 'Errore di rete. Riconnettiti.',
		app_name: 'Teatro Galassia'
	}),
	tr: pack({
		retry: 'Yeniden', view: 'Gör', close: 'Kapat', device_login: 'Cihazla giriş',
		google_login: 'Google ile giriş', continue_game: 'Devam', start_game: 'Başla',
		saves: 'Kayıtlar', gallery: 'Açılanlar', logout: 'Çıkış', landscape: 'Yatay', portrait: 'Dikey',
		back: 'Geri', save: 'Kaydet', screen: 'Ekran', sound: 'Ses', off: 'Kapalı', on: 'Açık',
		choose: 'Seç', tap: 'Sürdürmek için dokun', start_over: 'Yeniden başla', ending: 'Son',
		videos: 'Video', portraits: 'Portre', locked: 'Kilitli', load: 'Yükle', delete: 'Sil', language: 'Dil',
		network_error: 'Ağ hatası. Lütfen yeniden bağlanın.',
		app_name: 'Galaksi Tiyatrosu'
	}),
	pl: pack({
		retry: 'Ponów', view: 'Zobacz', close: 'Zamknij', device_login: 'Logowanie urządzeniem',
		google_login: 'Logowanie Google', continue_game: 'Kontynuuj', start_game: 'Start',
		saves: 'Zapisy', gallery: 'Odblokowane', logout: 'Wyloguj', landscape: 'Poziomo', portrait: 'Pionowo',
		back: 'Wstecz', save: 'Zapisz', screen: 'Ekran', sound: 'Dźwięk', off: 'Wył', on: 'Wł',
		choose: 'Wybierz', tap: 'Dotknij, aby kontynuować', start_over: 'Od nowa', ending: 'Zakończenie',
		videos: 'Wideo', portraits: 'Portrety', locked: 'Zablokowane', load: 'Wczytaj', delete: 'Usuń', language: 'Język',
		network_error: 'Błąd sieci. Połącz się ponownie.',
		app_name: 'Teatr Galaktyka'
	}),
	nl: pack({
		retry: 'Opnieuw', view: 'Bekijk', close: 'Sluiten', device_login: 'Inloggen met apparaat',
		google_login: 'Inloggen met Google', continue_game: 'Doorgaan', start_game: 'Start',
		saves: 'Saves', gallery: 'Ontgrendeld', logout: 'Afmelden', landscape: 'Liggend', portrait: 'Staand',
		back: 'Terug', save: 'Opslaan', screen: 'Scherm', sound: 'Geluid', off: 'Uit', on: 'Aan',
		choose: 'Kies', tap: 'Tik om verder te gaan', start_over: 'Opnieuw', ending: 'Einde',
		videos: 'Video’s', portraits: 'Portretten', locked: 'Vergrendeld', load: 'Laden', delete: 'Wissen', language: 'Taal',
		network_error: 'Netwerkfout. Maak opnieuw verbinding.',
		app_name: 'Galaxietheater'
	}),
	hi: pack({
		retry: 'फिर कोशिश', view: 'देखें', close: 'बंद', device_login: 'डिवाइस से साइन इन',
		google_login: 'Google साइन इन', continue_game: 'जारी रखें', start_game: 'शुरू',
		saves: 'सेव', gallery: 'अनलॉक', logout: 'बाहर', landscape: 'क्षैतिज', portrait: 'ऊर्ध्व',
		back: 'वापस', save: 'सेव', screen: 'स्क्रीन', sound: 'आवाज़', off: 'बंद', on: 'चालू',
		choose: 'चुनें', tap: 'आगे बढ़ने के लिए टैप', start_over: 'फिर से', ending: 'अंत',
		videos: 'वीडियो', portraits: 'चित्र', locked: 'लॉक', load: 'लोड', delete: 'हटाएँ', language: 'भाषा',
		network_error: 'नेटवर्क में समस्या है। फिर से कनेक्ट करें।',
		app_name: 'गैलेक्सी थिएटर'
	}),
	ms: pack({
		retry: 'Cuba lagi', view: 'Lihat', close: 'Tutup', device_login: 'Log masuk peranti',
		google_login: 'Log masuk Google', continue_game: 'Teruskan', start_game: 'Mula',
		saves: 'Simpanan', gallery: 'Dibuka', logout: 'Keluar', landscape: 'Melintang', portrait: 'Menegak',
		back: 'Kembali', save: 'Simpan', screen: 'Skrin', sound: 'Bunyi', off: 'Tutup', on: 'Buka',
		choose: 'Pilih', tap: 'Ketik untuk terus', start_over: 'Mula semula', ending: 'Tamat',
		videos: 'Video', portraits: 'Potret', locked: 'Terkunci', load: 'Muat', delete: 'Padam', language: 'Bahasa',
		network_error: 'Rangkaian tidak normal. Sila sambung semula.',
		app_name: 'Teater Galaksi'
	}),
	fil: pack({
		retry: 'Subukan muli', view: 'Tingnan', close: 'Isara', device_login: 'Sign-in sa device',
		google_login: 'Google sign-in', continue_game: 'Ipagpatuloy', start_game: 'Simulan',
		saves: 'Saves', gallery: 'Unlocked', logout: 'Lumabas', landscape: 'Pahiga', portrait: 'Patayo',
		back: 'Bumalik', save: 'I-save', screen: 'Screen', sound: 'Tunog', off: 'Off', on: 'On',
		choose: 'Pumili', tap: 'I-tap para magpatuloy', start_over: 'Ulitin', ending: 'Wakas',
		videos: 'Video', portraits: 'Larawan', locked: 'Naka-lock', load: 'I-load', delete: 'Burahin', language: 'Wika',
		network_error: 'May problema sa network. Kumonekta muli.',
		app_name: 'Galaxy Theatre'
	}),
	sv: pack({
		retry: 'Försök igen', view: 'Visa', close: 'Stäng', device_login: 'Logga in med enhet',
		google_login: 'Logga in med Google', continue_game: 'Fortsätt', start_game: 'Starta',
		saves: 'Sparningar', gallery: 'Upplåst', logout: 'Logga ut', landscape: 'Liggande', portrait: 'Stående',
		back: 'Tillbaka', save: 'Spara', screen: 'Skärm', sound: 'Ljud', off: 'Av', on: 'På',
		choose: 'Välj', tap: 'Tryck för att fortsätta', start_over: 'Börja om', ending: 'Slut',
		videos: 'Video', portraits: 'Porträtt', locked: 'Låst', load: 'Läs in', delete: 'Radera', language: 'Språk',
		network_error: 'Nätverksfel. Anslut igen.',
		app_name: 'Galaxteatern'
	})
}

const KEY = 'otome_lang'

function normalize(raw) {
	const text = String(raw || '').replace('_', '-')
	const lowered = text.toLowerCase()
	if (!lowered) return ''
	if (lowered.indexOf('hant') >= 0 || lowered === 'zh-tw' || lowered === 'zh-hk' || lowered === 'zh-mo') {
		return 'zh-Hant'
	}
	if (lowered.indexOf('zh') === 0) return 'zh-Hans'
	const primary = lowered.split('-')[0]
	const alias = { tl: 'fil' }
	const code = alias[primary] || primary
	return LANGS.some((item) => item.code === code) ? code : ''
}

function read() {
	try {
		const saved = normalize(uni.getStorageSync(KEY))
		if (saved) return saved
		const info = uni.getSystemInfoSync()
		return normalize(info.language) || 'zh-Hans'
	} catch (err) {
		return 'zh-Hans'
	}
}

export const lang = ref(read())

export function currentLang() {
	return lang.value
}

export function setLang(code) {
	const next = normalize(code) || 'zh-Hans'
	lang.value = next
	try {
		uni.setStorageSync(KEY, next)
	} catch (err) {
		// 语言仍保存在当前页面
	}
}

export function t(key, vars) {
	const pack = PACKS[lang.value] || zh
	let text = pack[key] || en[key] || zh[key] || key
	if (vars) {
		Object.keys(vars).forEach((name) => {
			text = text.split('{' + name + '}').join(String(vars[name]))
		})
	}
	return text
}
