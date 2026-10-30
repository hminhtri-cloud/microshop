import { useEffect, useState, type FormEvent } from 'react';
import { Link, useParams } from 'react-router-dom';

import { api, errorMessage, type Product, type ProductInput, type ProductPage } from './api';
import { useCart } from './cartState';
import { Icon, Loading, Notice } from './ui';

export function formatPrice(value: string) {
  return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(Number(value));
}

export function ProductImage({ product }: { product: Product }) {
  const [failed, setFailed] = useState(false);
  return <div className="product-image">
    {product.image_url && !failed ? <img src={product.image_url} alt={product.name} loading="lazy" onError={() => setFailed(true)} /> : <Icon name="bag" size={42} />}
  </div>;
}

export function ProductTile({ product }: { product: Product }) {
  const { add } = useCart();
  const [message, setMessage] = useState<{ text: string; success: boolean } | null>(null);
  function quickAdd() {
    try { add(product); setMessage({ text: 'Đã thêm vào giỏ hàng.', success: true }); }
    catch (err) { setMessage({ text: errorMessage(err), success: false }); }
  }
  return <article className="product-card"><Link to={`/products/${product.id}`}><ProductImage product={product} /><div className="product-copy"><span className="eyebrow">{product.category}</span><h2>{product.name}</h2><strong>{formatPrice(product.price)}</strong><span className="muted">Cửa hàng #{product.seller_id} · Còn {product.quantity} sản phẩm</span></div></Link><div className="product-card-actions"><button className="button secondary compact" type="button" onClick={quickAdd} disabled={product.quantity < 1}>Thêm vào giỏ</button>{message && <span role={message.success ? 'status' : 'alert'} className={message.success ? '' : 'cart-warning'}>{message.text}</span>}</div></article>;
}

export function Catalog() {
  const [search, setSearch] = useState('');
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState('');
  const [offset, setOffset] = useState(0);
  const [page, setPage] = useState<ProductPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError('');
    api.products({ search: query, category, offset }, controller.signal)
      .then(result => { if (!controller.signal.aborted) setPage(result); })
      .catch((err: unknown) => { if (!controller.signal.aborted) setError(errorMessage(err)); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [query, category, offset]);

  function submit(event: FormEvent) {
    event.preventDefault(); setOffset(0); setQuery(search.trim());
  }
  return <section className="container page"><div className="page-heading"><div><span className="eyebrow">KHÁM PHÁ MICROSHOP</span><h1>Sản phẩm từ cộng đồng.</h1><p>Tìm món đồ bạn thích từ những cửa hàng trong marketplace.</p></div></div>
    <form className="catalog-search" onSubmit={submit}><input aria-label="Tìm sản phẩm" placeholder="Tìm theo tên sản phẩm…" value={search} onChange={event => setSearch(event.target.value)} maxLength={120} /><button className="button primary" type="submit">Tìm kiếm</button><input aria-label="Lọc danh mục" placeholder="Danh mục (ví dụ: Phụ kiện)" value={category} onChange={event => { setCategory(event.target.value); setOffset(0); }} maxLength={60} /></form>
    {error && <Notice>{error}</Notice>}
    {loading ? <Loading /> : page && <>{page.items.length === 0 ? <div className="panel empty-state"><Icon name="shop" size={38} /><h2>Chưa có sản phẩm phù hợp</h2><p>Thử từ khóa khác hoặc ghé lại sau khi các seller đăng sản phẩm nhé.</p></div> : <div className="product-grid">{page.items.map(product => <ProductTile product={product} key={product.id} />)}</div>}
      <div className="pagination"><span>{page.total} sản phẩm</span><div className="button-row"><button className="button secondary compact" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 12))}>Trước</button><button className="button secondary compact" disabled={offset + 12 >= page.total} onClick={() => setOffset(offset + 12)}>Sau</button></div></div>
    </>}
  </section>;
}

export function ProductDetail() {
  const { id } = useParams();
  const { add } = useCart();
  const [quantity, setQuantity] = useState(1);
  const [message, setMessage] = useState<{ text: string; success: boolean } | null>(null);
  const [product, setProduct] = useState<Product | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    if (!id || !/^\d+$/.test(id) || Number(id) <= 0) { setError('Sản phẩm không tồn tại.'); setLoading(false); return; }
    let active = true;
    api.product(Number(id)).then(value => { if (active) setProduct(value); })
      .catch((err: unknown) => { if (active) setError(errorMessage(err)); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [id]);
  function addToCart() {
    if (!product) return;
    try { add(product, quantity); setMessage({ text: 'Đã thêm sản phẩm vào giỏ hàng.', success: true }); }
    catch (err) { setMessage({ text: errorMessage(err), success: false }); }
  }
  return <section className="container page"><Link className="subtle-link" to="/products">← Quay lại danh sách</Link>{loading ? <Loading /> : error ? <Notice>{error}</Notice> : product && <div className="detail-grid"><ProductImage product={product} /><div><span className="eyebrow">{product.category} · CỬA HÀNG #{product.seller_id}</span><h1>{product.name}</h1><strong className="detail-price">{formatPrice(product.price)}</strong><p className="muted preserve-lines">{product.description}</p><p className="muted">Số lượng hiện có: {product.quantity}</p><div className="detail-actions"><label>Số lượng<input type="number" aria-label="Số lượng thêm vào giỏ" min="1" max={Math.min(product.quantity, 99)} value={quantity} onChange={event => setQuantity(Number(event.target.value))} disabled={product.quantity < 1} /></label><button className="button primary" disabled={product.quantity < 1 || !Number.isInteger(quantity) || quantity < 1 || quantity > Math.min(product.quantity, 99)} onClick={addToCart}>Thêm vào giỏ <Icon name="bag" size={17} /></button><Link to="/cart" className="button secondary">Xem giỏ hàng</Link></div>{message && <Notice success={message.success}>{message.text}</Notice>}<div className="development-note">Giỏ hàng hiện lưu trên trình duyệt; đặt hàng sẽ có sau khi Order Service hoàn thành.</div></div></div>}</section>;
}

const blankProduct: ProductInput = { name: '', description: '', category: '', price: '', quantity: 0, image_url: null };

export function SellerProducts() {
  const [items, setItems] = useState<Product[]>([]);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [reload, setReload] = useState(0);
  const [editing, setEditing] = useState<Product | null>(null);
  const [form, setForm] = useState<ProductInput>({ ...blankProduct });

  useEffect(() => {
    let active = true;
    setLoading(true); setError('');
    api.sellerProducts().then(page => { if (active) setItems(page.items); })
      .catch((err: unknown) => { if (active) setError(errorMessage(err)); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [reload]);

  async function save(event: FormEvent) {
    event.preventDefault(); setError(''); setSuccess('');
    if (!form.name.trim() || !form.description.trim() || !form.category.trim() || !/^\d+(\.\d{1,2})?$/.test(form.price) || Number(form.price) === 0) {
      setError('Điền đầy đủ tên, danh mục, mô tả và giá dương (tối đa 2 số lẻ).'); return;
    }
    setBusy(true);
    try {
      const input = { ...form, name: form.name.trim(), description: form.description.trim(), category: form.category.trim(), image_url: form.image_url?.trim() || null };
      if (editing) await api.updateProduct(editing.id, input);
      else await api.createProduct(input);
      setSuccess(editing ? 'Đã cập nhật sản phẩm.' : 'Đã đăng sản phẩm mới.');
      setEditing(null); setForm({ ...blankProduct }); setReload(value => value + 1);
    } catch (err) { setError(errorMessage(err)); }
    finally { setBusy(false); }
  }

  async function visibility(product: Product) {
    setBusy(true); setError(''); setSuccess('');
    try {
      await api.sellerVisibility(product.id, product.status === 'active' ? 'hidden' : 'active');
      setSuccess('Đã cập nhật trạng thái hiển thị.'); setReload(value => value + 1);
    } catch (err) { setError(errorMessage(err)); }
    finally { setBusy(false); }
  }

  return <section className="container page"><div className="page-heading"><div><span className="eyebrow">QUẢN LÝ CỬA HÀNG</span><h1>Sản phẩm của shop.</h1><p>Đăng sản phẩm, chỉnh sửa thông tin và quản lý hiển thị.</p></div><Link className="button secondary" to="/seller">← Hồ sơ người bán</Link></div>
    {error && <Notice>{error}</Notice>}{success && <Notice success>{success}</Notice>}
    <div className="seller-grid"><article className="panel"><h2>{editing ? `Chỉnh sửa #${editing.id}` : 'Đăng sản phẩm mới'}</h2><p className="muted">Giá nhập bằng chuỗi số để tránh sai lệch khi xử lý tiền.</p><form onSubmit={save}><fieldset disabled={busy}>
      <label>Tên sản phẩm<input required minLength={3} maxLength={120} value={form.name} onChange={event => setForm({ ...form, name: event.target.value })} /></label>
      <label>Mô tả<textarea required minLength={10} maxLength={2000} rows={4} value={form.description} onChange={event => setForm({ ...form, description: event.target.value })} /></label>
      <label>Danh mục<input required minLength={2} maxLength={60} value={form.category} onChange={event => setForm({ ...form, category: event.target.value })} /></label>
      <div className="form-pair"><label>Giá (VND)<input required inputMode="decimal" placeholder="125000.00" value={form.price} onChange={event => setForm({ ...form, price: event.target.value })} /></label><label>Tồn kho<input required type="number" min="0" step="1" value={form.quantity} onChange={event => setForm({ ...form, quantity: Number(event.target.value) })} /></label></div>
      <label>URL ảnh (tùy chọn)<input type="url" maxLength={500} placeholder="https://..." value={form.image_url || ''} onChange={event => setForm({ ...form, image_url: event.target.value })} /></label>
      <div className="button-row"><button className="button primary" type="submit">{busy ? 'Đang lưu…' : editing ? 'Lưu thay đổi' : 'Đăng sản phẩm'}</button>{editing && <button type="button" className="button secondary" onClick={() => { setEditing(null); setForm({ ...blankProduct }); }}>Hủy sửa</button>}</div>
    </fieldset></form></article><div className="panel"><h2>Sản phẩm đã đăng</h2>{loading ? <Loading /> : items.length ? <div className="manage-list">{items.map(product => <div className="manage-item" key={product.id}><strong>{product.name}</strong><span className="muted">#{product.id} · {formatPrice(product.price)} · Còn {product.quantity} · {product.status === 'active' ? 'Đang hiển thị' : product.status === 'blocked' ? 'Admin đã khóa' : 'Đang ẩn'}</span><div className="button-row"><button className="button secondary compact" onClick={() => { setEditing(product); setForm({ name: product.name, description: product.description, category: product.category, price: product.price, quantity: product.quantity, image_url: product.image_url }); }} disabled={busy || product.status === 'blocked'}>Sửa</button><button className="button secondary compact" onClick={() => void visibility(product)} disabled={busy || product.status === 'blocked'}>{product.status === 'active' ? 'Ẩn' : 'Hiện'}</button></div></div>)}</div> : <p className="muted">Shop chưa đăng sản phẩm nào. Hãy tạo sản phẩm đầu tiên!</p>}</div></div>
  </section>;
}

export function AdminProducts() {
  const [items, setItems] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [revision, setRevision] = useState(0);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    let active = true;
    setLoading(true); setError('');
    api.adminProducts().then(page => { if (active) setItems(page.items); })
      .catch((err: unknown) => { if (active) setError(errorMessage(err)); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [revision]);
  async function moderate(product: Product) {
    setBusy(true); setError(''); setSuccess('');
    try {
      await api.moderateProduct(product.id, product.status === 'blocked' ? 'active' : 'blocked');
      setSuccess('Đã cập nhật trạng thái sản phẩm.'); setRevision(value => value + 1);
    } catch (err) { setError(errorMessage(err)); }
    finally { setBusy(false); }
  }
  return <section className="container page"><div className="page-heading"><div><span className="eyebrow">ADMIN WORKSPACE</span><h1>Kiểm duyệt sản phẩm.</h1><p>Ẩn sản phẩm vi phạm; seller không thể tự mở lại sản phẩm bị khóa.</p></div><Link className="button secondary" to="/admin">← Hồ sơ seller</Link></div>{error && <Notice>{error}</Notice>}{success && <Notice success>{success}</Notice>}<article className="panel">{loading ? <Loading /> : items.length ? <div className="manage-list">{items.map(product => <div key={product.id} className="manage-item"><strong>{product.name}</strong><span className="muted">Seller #{product.seller_id} · {formatPrice(product.price)} · {product.status}</span><button className={`button compact ${product.status === 'blocked' ? 'secondary' : 'danger'}`} disabled={busy} onClick={() => void moderate(product)}>{product.status === 'blocked' ? 'Mở khóa' : 'Khóa sản phẩm'}</button></div>)}</div> : <p className="muted">Chưa có sản phẩm nào.</p>}</article></section>;
}
