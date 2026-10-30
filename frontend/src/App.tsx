import { useEffect, useState, type FormEvent, type ReactNode } from 'react';
import { Link, NavLink, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import { api, ApiError, errorMessage, session, type ApplicationPage, type ReviewAction, type SellerApplication } from './api';
import { useAuth } from './auth';
import { Badge, dateLabel, Icon, Loading, Notice, statuses } from './ui';
import { AdminProducts, Catalog, ProductDetail, SellerProducts } from './Products';
import { useCart } from './cartState';
import { CartPage } from './CartPage';
import { StorefrontHome } from './Storefront';
import { WorkspaceLayout } from './Workspace';

const roleNames = { customer: 'Khách hàng', seller: 'Người bán', admin: 'Quản trị viên' };

function Header() {
  const { user, logout } = useAuth();
  const { count } = useCart();
  const { pathname } = useLocation();
  const workspace = pathname.startsWith('/seller') || pathname.startsWith('/admin');
  const navigate = useNavigate();
  return <header className="header"><div className="container header-inner">
    <Link to="/" className="brand" aria-label="MicroShop trang chủ"><span className="brand-icon"><Icon /></span>micro<span>shop</span><span className="brand-dot">.</span></Link>
    {workspace ? <nav className="primary-nav" aria-label="Điều hướng chung"><Link to="/products">← Về khu mua sắm</Link></nav> : <nav className="primary-nav" aria-label="Điều hướng chính">
      <NavLink to="/" end>Trang chủ</NavLink>
      <NavLink to="/products">Sản phẩm</NavLink>
      <NavLink to="/cart" className="cart-nav">Giỏ hàng <span className="cart-count" aria-label={`${count} sản phẩm trong giỏ`}>{count}</span></NavLink>
      {user && <NavLink to="/account">Tài khoản</NavLink>}
      <NavLink to={user?.role === 'admin' ? '/admin' : '/seller'}>{user?.role === 'admin' ? 'Quản trị' : user?.role === 'seller' ? 'Kênh người bán' : 'Bán hàng'}</NavLink>
    </nav>}
    <div className="header-actions">{user ? <>
      <span className="user-chip" title={user.email}><span className="avatar small">{user.username.slice(0, 1).toUpperCase()}</span>{user.username}</span>
      <button className="button text-button" onClick={() => { logout(); navigate('/login'); }}>Đăng xuất</button>
    </> : <><Link className="login-link" to="/login">Đăng nhập</Link><Link className="button primary compact" to="/register">Đăng ký <Icon name="arrow" size={16} /></Link></>}</div>
  </div></header>;
}

function AuthPage({ register = false }: { register?: boolean }) {
  const auth = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [registered, setRegistered] = useState(false);
  const [email, setEmail] = useState('');
  if (auth.user) return <Navigate to="/account" replace />;
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const password = String(data.get('password'));
    if (new TextEncoder().encode(password).length > 72) { setError('Mật khẩu tối đa 72 byte UTF-8. Vui lòng dùng mật khẩu ngắn hơn.'); return; }
    if (register && password !== data.get('confirm')) { setError('Mật khẩu xác nhận chưa khớp.'); return; }
    setError(''); setBusy(true);
    try {
      if (register) {
        await api.register(String(data.get('username')).trim(), email.trim(), password);
        setRegistered(true);
      } else {
        await auth.login(email.trim(), password);
        navigate('/account', { replace: true });
      }
    } catch (err) { setError(errorMessage(err)); }
    finally { setBusy(false); }
  }
  return <section className="container auth-layout"><aside className="auth-aside"><span className="eyebrow">HELLO, MICROSHOP!</span><h1>{register ? <>Mỗi cửa hàng lớn<br />bắt đầu từ một<br /><span>ý tưởng nhỏ.</span></> : <>Thật vui<br />khi bạn<br /><span>quay trở lại.</span></>}</h1><p>Mua sắm, kết nối và phát triển cửa hàng của bạn trong cùng một không gian.</p><div className="aside-art"><Icon name="shop" size={100} /><div className="orbit orbit-one" /><div className="orbit orbit-two" /></div><div className="aside-caption">Dành cho người mua. Đồng hành cùng người bán.</div></aside>
    <div className="auth-form-wrap"><div className="auth-form">
      {registered ? <><div className="success-icon"><Icon name="check" size={30} /></div><h2>Tài khoản đã sẵn sàng!</h2><p className="muted">Đã đăng ký <strong>{email}</strong>. Đăng nhập để quản lý tài khoản hoặc gửi hồ sơ mở shop.</p><Link to="/login" className="button primary full">Đến trang đăng nhập <Icon name="arrow" size={18} /></Link></> : <>
        <span className="eyebrow">{register ? 'THAM GIA CÙNG CHÚNG TÔI' : 'CHÀO MỪNG TRỞ LẠI'}</span><h2>{register ? 'Tạo tài khoản' : 'Đăng nhập'}</h2><p className="muted">{register ? 'Chỉ vài thông tin để bắt đầu hành trình mới.' : 'Tiếp tục hành trình của bạn tại MicroShop.'}</p>
        {(error || auth.error) && <Notice>{error || auth.error}</Notice>}
        <form onSubmit={submit}><fieldset disabled={busy}>
          {register && <label>Tên người dùng<input name="username" autoComplete="username" placeholder="Ví dụ: minhtri" required minLength={3} maxLength={50} pattern=".*\S.*" /></label>}
          <label>Email<input type="email" name="email" autoComplete="email" placeholder="ban@example.com" required value={email} onChange={(e) => setEmail(e.target.value)} /></label>
          <label><span id="password-label">Mật khẩu</span><div className="password-field"><input aria-labelledby="password-label" name="password" type={showPassword ? 'text' : 'password'} autoComplete={register ? 'new-password' : 'current-password'} placeholder={register ? 'Tối thiểu 8 ký tự' : 'Nhập mật khẩu của bạn'} minLength={register ? 8 : 1} maxLength={72} required /><button type="button" aria-label={showPassword ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'} onClick={() => setShowPassword(!showPassword)}>{showPassword ? 'Ẩn' : 'Hiện'}</button></div></label>
          {register && <><label>Xác nhận mật khẩu<input name="confirm" type={showPassword ? 'text' : 'password'} autoComplete="new-password" placeholder="Nhập lại mật khẩu" required minLength={8} maxLength={72} /></label><p className="field-help">Tài khoản mới có quyền khách hàng. Bạn có thể đăng ký bán hàng sau khi đăng nhập.</p></>}
          <button className="button primary full" type="submit">{busy ? 'Đang xử lý…' : register ? 'Tạo tài khoản' : 'Đăng nhập'} {!busy && <Icon name="arrow" size={18} />}</button>
        </fieldset></form>
        <p className="auth-switch">{register ? 'Đã có tài khoản?' : 'Chưa có tài khoản?'} <Link to={register ? '/login' : '/register'}>{register ? 'Đăng nhập' : 'Đăng ký ngay'}</Link></p>
      </>}
    </div></div></section>;
}

function Protected({ children, admin = false, seller = false }: { children: ReactNode; admin?: boolean; seller?: boolean }) {
  const auth = useAuth();
  if (auth.loading) return <Loading />;
  if (!auth.user) {
    if (session.get() && auth.error) return <section className="container page"><Notice>{auth.error}</Notice><button className="button secondary" onClick={() => void auth.refresh()}>Thử lại</button></section>;
    return <Navigate to="/login" replace />;
  }
  if ((admin && auth.user.role !== 'admin') || (seller && auth.user.role !== 'seller')) return <section className="container page"><h1>Bạn không có quyền truy cập</h1><p>Trang này dành cho tài khoản đã được cấp quyền phù hợp.</p><Link className="button primary" to="/account">Về tài khoản</Link></section>;
  return <>{children}</>;
}

function Account() {
  const { user, error, refresh } = useAuth();
  if (!user) return null;
  return <section className="container page"><div className="page-heading"><div><span className="eyebrow">KHÔNG GIAN CỦA BẠN</span><h1>Xin chào, {user.username} <span className="wave">✦</span></h1><p>Quản lý tài khoản và tiếp tục hành trình cùng MicroShop.</p></div><button className="button secondary" onClick={() => void refresh()}>Cập nhật quyền</button></div>
    {error && <Notice>{error}</Notice>}
    <div className="account-grid"><article className="panel account-card"><span className="avatar">{user.username.slice(0, 1).toUpperCase()}</span><h2>{user.username}</h2><span className="role-label">{roleNames[user.role]}</span><dl className="details"><div><dt>Email</dt><dd>{user.email}</dd></div><div><dt>Mã tài khoản</dt><dd>#{user.id}</dd></div><div><dt>Ngày tham gia</dt><dd>{dateLabel(user.created_at)}</dd></div></dl></article>
    <article className="panel callout"><span className="icon-tile"><Icon name={user.role === 'admin' ? 'shield' : 'shop'} size={30} /></span><h2>{user.role === 'admin' ? 'Chăm sóc cộng đồng người bán' : user.role === 'seller' ? 'Không gian dành cho shop của bạn' : 'Bạn có một ý tưởng kinh doanh?'}</h2><p>{user.role === 'admin' ? 'Kiểm tra hồ sơ, duyệt shop mới và quản lý trạng thái người bán.' : 'Theo dõi hồ sơ cửa hàng và quyền bán hàng tại một nơi. Mỗi hành trình đều bắt đầu từ bước đầu tiên.'}</p><Link className="button primary" to={user.role === 'admin' ? '/admin' : '/seller'}>{user.role === 'admin' ? 'Quản lý hồ sơ seller' : 'Đến kênh người bán'} <Icon name="arrow" size={18} /></Link>{user.role === 'seller' && <Link className="subtle-link" to="/seller/products">Quản lý sản phẩm →</Link>}{user.role === 'admin' && <Link className="subtle-link" to="/admin/products">Kiểm duyệt sản phẩm →</Link>}</article></div>
  </section>;
}

function SellerPage() {
  const { user, refresh } = useAuth();
  const [application, setApplication] = useState<SellerApplication | null>(null);
  const [loading, setLoading] = useState(true);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [busy, setBusy] = useState(false);
  const [shop, setShop] = useState('');
  const [description, setDescription] = useState('');
  const [reload, setReload] = useState(0);

  useEffect(() => {
    let active = true;
    setLoading(true); setError(''); setLoaded(false);
    api.application().then((result) => {
      if (!active) return;
      setApplication(result); setShop(result.shop_name); setDescription(result.description); setLoaded(true);
    }).catch((err: unknown) => {
      if (!active) return;
      if (err instanceof ApiError && err.status === 404) { setApplication(null); setLoaded(true); }
      else setError(errorMessage(err));
    }).finally(() => { if (active) setLoading(false); });
    void refresh();
    return () => { active = false; };
  }, [reload, refresh]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(''); setSuccess(''); setBusy(true);
    if (shop.trim().length < 3 || description.trim().length < 10) {
      setError('Tên shop cần ít nhất 3 ký tự, mô tả ít nhất 10 ký tự (không tính khoảng trắng đầu/cuối).'); setBusy(false); return;
    }
    try {
      const result = await api.apply(shop.trim(), description.trim());
      setApplication(result); setSuccess('Đã gửi hồ sơ! Bạn có thể theo dõi kết quả ngay tại đây.');
      await refresh();
    } catch (err) { setError(errorMessage(err)); }
    finally { setBusy(false); }
  }
  if (user?.role === 'admin') return <Navigate to="/admin" replace />;
  const canEdit = loaded && (!application || application.status === 'rejected');
  return <section className="container page"><div className="page-heading"><div><span className="eyebrow">SELLER CENTER</span><h1>Góc nhỏ của người bán.</h1><p>Giới thiệu cửa hàng và theo dõi hành trình trở thành seller.</p></div><div className="button-row">{user?.role === 'seller' && <Link className="button primary" to="/seller/products">Quản lý sản phẩm</Link>}<button className="button secondary" disabled={loading || busy} onClick={() => { setSuccess(''); setReload(reload + 1); }}>Tải lại trạng thái</button></div></div>
    {error && <Notice>{error}</Notice>}{success && <Notice success>{success}</Notice>}
    {loading ? <Loading /> : loaded && <div className="seller-grid"><div>
      {application && <article className="panel application-summary"><div className="card-heading"><span className="icon-tile"><Icon name="shop" /></span><Badge status={application.status} /></div><h2>{application.shop_name}</h2><p className="preserve-lines">{application.description}</p><div className="status-description">{statuses[application.status].detail}</div>{application.review_note && <blockquote><span>Phản hồi từ quản trị viên</span><p>{application.review_note}</p></blockquote>}<div className="meta">Hồ sơ #{application.id} · Cập nhật {dateLabel(application.updated_at)}</div></article>}
      {canEdit && <article className="panel"><h2>{application ? 'Cập nhật và gửi lại hồ sơ' : 'Đăng ký cửa hàng'}</h2><p className="muted">Cho chúng tôi biết một chút về cửa hàng bạn muốn xây dựng.</p><form onSubmit={submit}><fieldset disabled={busy}><label>Tên cửa hàng<input name="shop_name" placeholder="Ví dụ: Blue Tech Shop" required minLength={3} maxLength={100} value={shop} onChange={(e) => setShop(e.target.value)} /></label><label>Giới thiệu cửa hàng<textarea name="description" rows={5} placeholder="Bạn dự định bán những sản phẩm gì? Điều gì làm shop của bạn đặc biệt?" required minLength={10} maxLength={1000} value={description} onChange={(e) => setDescription(e.target.value)} /></label><div className="field-help align-right">{description.length}/1000 ký tự</div><button className="button primary" type="submit">{busy ? 'Đang gửi…' : application ? 'Gửi lại hồ sơ' : 'Gửi hồ sơ đăng ký'} <Icon name="arrow" size={18} /></button></fieldset></form></article>}
    </div><aside className="panel guide"><span className="eyebrow">NHỮNG ĐIỀU CẦN BIẾT</span><h3>Một hồ sơ, một khởi đầu.</h3><ol><li><strong>Thông tin rõ ràng</strong><p>Tên shop dễ nhận biết, mô tả đúng định hướng kinh doanh.</p></li><li><strong>Đợi xét duyệt</strong><p>Quản trị viên sẽ phản hồi ngay trong hồ sơ của bạn.</p></li><li><strong>Nhận quyền seller</strong><p>Sau khi được duyệt, tài khoản được cấp quyền người bán.</p></li></ol><div className="development-note">Seller đã được duyệt có thể đăng sản phẩm ở mục Quản lý sản phẩm.</div></aside></div>}
  </section>;
}

function AdminPage() {
  const [filter, setFilter] = useState('pending');
  const [offset, setOffset] = useState(0);
  const [page, setPage] = useState<ApplicationPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [revision, setRevision] = useState(0);
  const [review, setReview] = useState<{ item: SellerApplication; action: ReviewAction } | null>(null);
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [reviewError, setReviewError] = useState('');
  const actionNames = { approve: 'Duyệt hồ sơ', reject: 'Từ chối hồ sơ', suspend: 'Tạm ngưng seller' };
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError(''); setPage(null);
    api.applications(filter, offset, controller.signal).then((result) => {
      if (controller.signal.aborted) return;
      if (offset > 0 && result.items.length === 0) setOffset(Math.max(0, offset - 10));
      else setPage(result);
    }).catch((err: unknown) => { if (!controller.signal.aborted) setError(errorMessage(err)); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [filter, offset, revision]);

  function startReview(item: SellerApplication, action: ReviewAction) {
    setReview({ item, action }); setNote(''); setReviewError(''); setSuccess('');
  }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!review) return;
    if (note.trim().length < 3) { setReviewError('Vui lòng nhập lý do ít nhất 3 ký tự.'); return; }
    setBusy(true); setReviewError('');
    try {
      await api.review(review.item.id, review.action, note.trim());
      setSuccess(`Đã cập nhật hồ sơ “${review.item.shop_name}”.`);
      setReview(null); setRevision(revision + 1);
    } catch (err) { setReviewError(errorMessage(err)); }
    finally { setBusy(false); }
  }
  return <section className="container page"><div className="page-heading"><div><span className="eyebrow">ADMIN WORKSPACE</span><h1>Cộng đồng người bán.</h1><p>Xem xét hồ sơ và giữ cho cộng đồng MicroShop hoạt động minh bạch.</p></div><div className="button-row"><Link className="button secondary" to="/admin/products">Kiểm duyệt sản phẩm</Link><span className="admin-chip"><Icon name="shield" size={18} /> Quản trị viên</span></div></div>
    {success && <Notice success>{success}</Notice>}{error && <Notice>{error}</Notice>}
    <div className="panel admin-panel"><div className="admin-toolbar"><label>Lọc trạng thái<select value={filter} onChange={(e) => { setFilter(e.target.value); setOffset(0); }}><option value="">Tất cả trạng thái</option>{Object.entries(statuses).map(([key, value]) => <option key={key} value={key}>{value.label}</option>)}</select></label><div className="toolbar-right"><span className="muted">{page ? `${page.total} hồ sơ` : '…'}</span><button className="button secondary compact" disabled={loading} onClick={() => setRevision(revision + 1)}>Tải lại</button></div></div>
      {loading ? <Loading /> : page && <>{page.items.length ? <div className="application-list">{page.items.map((item) => <article className="admin-application" key={item.id}><div className="application-top"><div className="application-title"><span className="icon-tile"><Icon name="shop" /></span><div><h2>{item.shop_name}</h2><span className="meta">Hồ sơ #{item.id} · Tài khoản #{item.user_id}</span></div></div><Badge status={item.status} /></div><p className="preserve-lines">{item.description}</p>{item.review_note && <blockquote><span>Phản hồi gần nhất</span><p>{item.review_note}</p></blockquote>}<div className="application-bottom"><span className="meta">Cập nhật {dateLabel(item.updated_at)}</span><div className="button-row">{(item.status === 'pending' || item.status === 'suspended') && <button className="button primary compact" onClick={() => startReview(item, 'approve')}>{item.status === 'suspended' ? 'Khôi phục seller' : 'Duyệt hồ sơ'}</button>}{item.status === 'pending' && <button className="button danger compact" onClick={() => startReview(item, 'reject')}>Từ chối</button>}{item.status === 'approved' && <button className="button danger compact" onClick={() => startReview(item, 'suspend')}>Tạm ngưng</button>}</div></div></article>)}</div> : <div className="empty-state"><span className="icon-tile"><Icon name="check" size={30} /></span><h2>Không có hồ sơ ở đây</h2><p>Hãy chọn trạng thái khác hoặc tải lại để xem hồ sơ mới.</p></div>}
      <div className="pagination"><span>{page.total ? `${offset + 1}–${offset + page.items.length} / ${page.total} hồ sơ` : '0 hồ sơ'}</span><div className="button-row"><button className="button secondary compact" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 10))}>Trước</button><button className="button secondary compact" disabled={offset + 10 >= page.total} onClick={() => setOffset(offset + 10)}>Sau</button></div></div></>}
    </div>
    {review && <ReviewDialog title={actionNames[review.action]} busy={busy} onClose={() => setReview(null)}><p>Bạn đang cập nhật hồ sơ <strong>{review.item.shop_name}</strong>. Phản hồi sẽ được hiển thị cho chủ shop.</p>{reviewError && <Notice>{reviewError}</Notice>}<form onSubmit={submit}><fieldset disabled={busy}><label>Lý do / phản hồi<textarea autoFocus rows={4} minLength={3} maxLength={500} required value={note} onChange={(e) => setNote(e.target.value)} placeholder="Ghi rõ kết quả xét duyệt hoặc lý do thay đổi trạng thái…" /></label><div className="dialog-actions"><button type="button" className="button secondary" onClick={() => setReview(null)}>Hủy</button><button className={`button ${review.action === 'approve' ? 'primary' : 'danger-solid'}`} type="submit">{busy ? 'Đang cập nhật…' : 'Xác nhận'}</button></div></fieldset></form></ReviewDialog>}
  </section>;
}

function ReviewDialog({ title, busy, onClose, children }: { title: string; busy: boolean; onClose: () => void; children: ReactNode }) {
  const [element, setElement] = useState<HTMLDialogElement | null>(null);
  useEffect(() => { if (element && !element.open) element.showModal(); }, [element]);
  return <dialog ref={setElement} className="review-dialog" aria-labelledby="review-title" onCancel={(event) => { event.preventDefault(); if (!busy) onClose(); }}><h2 id="review-title">{title}</h2>{children}</dialog>;
}

export default function App() {
  return <div className="app"><Header /><main><Routes>
    <Route path="/" element={<StorefrontHome />} />
    <Route path="/products" element={<Catalog />} />
    <Route path="/products/:id" element={<ProductDetail />} />
    <Route path="/cart" element={<CartPage />} />
    <Route path="/login" element={<AuthPage key="login" />} />
    <Route path="/register" element={<AuthPage key="register" register />} />
    <Route path="/account" element={<Protected><Account /></Protected>} />
    <Route element={<Protected><WorkspaceLayout /></Protected>}>
      <Route path="/seller" element={<SellerPage />} />
      <Route path="/seller/products" element={<Protected seller><SellerProducts /></Protected>} />
    </Route>
    <Route element={<Protected admin><WorkspaceLayout admin /></Protected>}>
      <Route path="/admin" element={<AdminPage />} />
      <Route path="/admin/products" element={<AdminProducts />} />
    </Route>
    <Route path="*" element={<section className="container page"><h1>Trang này chưa tồn tại.</h1><Link className="button primary" to="/">Về trang chủ</Link></section>} />
  </Routes></main><footer className="footer"><div className="container footer-inner"><span><strong>microshop.</strong> Một khởi đầu, nhiều cơ hội.</span><span>Marketplace học tập · Đang phát triển</span></div></footer></div>;
}
