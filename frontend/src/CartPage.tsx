import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { api, ApiError, errorMessage, type Product } from './api';
import { useCart } from './cartState';
import { Icon, Loading, Notice } from './ui';

type Resolved = { status: 'available'; product: Product } | { status: 'unavailable' | 'error'; message: string };

function amountInCents(price: string, quantity: number): bigint {
  const [whole, fraction = ''] = price.split('.');
  if (!/^\d+$/.test(whole) || !/^\d{0,2}$/.test(fraction)) return 0n;
  return (BigInt(whole) * 100n + BigInt(fraction.padEnd(2, '0'))) * BigInt(quantity);
}

function money(cents: bigint): string {
  return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(cents / 100n);
}

export function CartPage() {
  const { lines, update, remove } = useCart();
  const [products, setProducts] = useState<Record<number, Resolved>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [revision, setRevision] = useState(0);
  const ids = lines.map(item => item.productId).join(',');

  useEffect(() => {
    const controller = new AbortController();
    if (!ids) { setProducts({}); setLoading(false); return () => controller.abort(); }
    setLoading(true);
    void Promise.all(ids.split(',').map(async value => {
      const id = Number(value);
      try {
        const product = await api.product(id, controller.signal);
        return [id, { status: 'available', product }] as const;
      } catch (err) {
        const status = err instanceof ApiError && err.status === 404 ? 'unavailable' : 'error';
        return [id, { status, message: errorMessage(err) }] as const;
      }
    })).then(entries => { if (!controller.signal.aborted) setProducts(Object.fromEntries(entries)); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [ids, revision]);

  function change(id: number, quantity: number, stock: number) {
    if (quantity > Math.min(stock, 99) || quantity < 1) return;
    try { update(id, quantity); setError(''); } catch (err) { setError(errorMessage(err)); }
  }

  const validated = lines.map(line => ({ line, result: products[line.productId] }));
  const invalid = validated.some(({ line, result }) => !result || result.status !== 'available' || line.quantity > result.product.quantity);
  const total = validated.reduce((sum, { line, result }) => result?.status === 'available' && line.quantity <= result.product.quantity
    ? sum + amountInCents(result.product.price, line.quantity) : sum, 0n);

  return <section className="container page"><div className="page-heading"><div><span className="eyebrow">KHÔNG GIAN MUA SẮM</span><h1>Giỏ hàng của bạn.</h1><p>Chọn sản phẩm yêu thích trước khi đặt hàng.</p></div><Link className="button secondary" to="/products">Tiếp tục mua sắm</Link></div>
    {error && <Notice>{error}</Notice>}
    {lines.length === 0 ? <div className="panel empty-state"><Icon name="bag" size={40} /><h2>Giỏ hàng đang trống</h2><p>Hãy khám phá những sản phẩm từ cộng đồng MicroShop.</p><Link className="button primary" to="/products">Khám phá sản phẩm</Link></div> : <div className="cart-layout"><div className="cart-items">
      {loading ? <Loading /> : validated.map(({ line, result }) => <article className="panel cart-item" key={line.productId}>
        {result?.status === 'available' ? <><div className="cart-thumb">{result.product.image_url ? <img src={result.product.image_url} alt="" onError={event => { event.currentTarget.style.display = 'none'; }} /> : <Icon name="bag" size={28} />}</div><div className="cart-item-info"><Link to={`/products/${line.productId}`} className="cart-title">{result.product.name}</Link><span className="muted">Shop #{result.product.seller_id} · {result.product.category}</span><strong>{money(amountInCents(result.product.price, 1))}</strong>{line.quantity > result.product.quantity && <span className="cart-warning">Chỉ còn {result.product.quantity} sản phẩm; hãy giảm số lượng hoặc xóa khỏi giỏ.</span>}</div>
          <div className="cart-controls"><div className="quantity-control"><button aria-label={`Giảm số lượng ${result.product.name}`} disabled={line.quantity <= 1} onClick={() => change(line.productId, line.quantity - 1, result.product.quantity)}>−</button><span aria-label={`Số lượng ${result.product.name}`}>{line.quantity}</span><button aria-label={`Tăng số lượng ${result.product.name}`} disabled={line.quantity >= Math.min(result.product.quantity, 99)} onClick={() => change(line.productId, line.quantity + 1, result.product.quantity)}>+</button></div><button className="button text-button" onClick={() => remove(line.productId)}>Xóa</button></div></> : <><div className="cart-thumb"><Icon name="bag" size={28} /></div><div className="cart-item-info"><strong>Sản phẩm #{line.productId}</strong><span className="cart-warning">{result?.message || 'Chưa kiểm tra được sản phẩm.'} Giỏ hàng vẫn giữ lại mục này.</span></div><button className="button secondary compact" onClick={() => remove(line.productId)}>Xóa khỏi giỏ</button></>}
        </article>)}
      </div><aside className="panel cart-summary"><span className="eyebrow">TỔNG KẾT GIỎ HÀNG</span><h2>Tạm tính</h2><div className="summary-row"><span>Sản phẩm</span><span>{lines.reduce((sum, line) => sum + line.quantity, 0)}</span></div><div className="summary-row total"><strong>Thành tiền dự kiến</strong><strong>{loading ? 'Đang kiểm tra…' : money(total)}</strong></div><p>Giá và tồn kho vừa được kiểm tra lại từ Product Service khi mở giỏ, nhưng có thể thay đổi bất cứ lúc nào. Backend sẽ phải xác nhận lại khi đặt hàng.</p>{invalid && !loading && <Notice>Giỏ có sản phẩm không còn hợp lệ hoặc vượt tồn kho. Hãy kiểm tra trước khi đặt hàng.</Notice>}<button className="button primary full" disabled title="Order Service chưa được triển khai">Đặt hàng — sắp ra mắt</button><button className="button secondary full refresh-cart" onClick={() => setRevision(value => value + 1)} disabled={loading}>Kiểm tra lại giá &amp; tồn kho</button></aside></div>}
  </section>;
}
