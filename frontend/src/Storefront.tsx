import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { api, errorMessage, type Product } from './api';
import { useAuth } from './auth';
import { Icon, Loading, Notice } from './ui';
import { ProductTile } from './Products';

export function StorefrontHome() {
  const { user } = useAuth();
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  useEffect(() => {
    const controller = new AbortController();
    api.products({}, controller.signal).then(page => setProducts(page.items.slice(0, 4)))
      .catch((err: unknown) => { if (!controller.signal.aborted) setError(errorMessage(err)); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, []);
  return <>
    <section className="storefront-hero"><div className="container storefront-hero-inner"><div>
      <span className="eyebrow">MUA SẮM CÙNG CỘNG ĐỒNG MICROSHOP</span>
      <h1>Khám phá món đồ<br />bạn yêu thích. <span>Mỗi ngày.</span></h1>
      <p>Khám phá sản phẩm từ nhiều cửa hàng, chọn món phù hợp và lưu lại trong giỏ hàng của riêng bạn.</p>
      <div className="button-row"><Link to="/products" className="button primary">Xem tất cả sản phẩm <Icon name="arrow" size={18} /></Link><Link to="/cart" className="button secondary">Giỏ hàng của tôi</Link></div>
    </div><div className="storefront-hero-art" aria-hidden="true"><span className="storefront-orb orb-one" /><span className="storefront-orb orb-two" /><div className="hero-market-card"><Icon name="bag" size={62} /><span>Sản phẩm từ cộng đồng</span></div><span className="hero-market-tag">Mua sắm theo cách của bạn ✦</span></div></div></section>
    <section className="container featured-section"><div className="section-heading"><div><span className="eyebrow">VỪA LÊN KỆ</span><h2>Sản phẩm mới</h2></div><Link className="subtle-link" to="/products">Khám phá tất cả →</Link></div>
      {error && <Notice>{error}</Notice>}
      {loading ? <Loading /> : products.length ? <div className="product-grid">{products.map(product => <ProductTile product={product} key={product.id} />)}</div> : <div className="panel empty-state"><Icon name="bag" size={38} /><h2>Đang chờ những sản phẩm đầu tiên</h2><p>Các cửa hàng sẽ sớm giới thiệu sản phẩm tại đây.</p><Link className="button secondary" to="/products">Đến danh mục</Link></div>}
    </section>
    <section className="container storefront-footer-cta"><div><span className="eyebrow">DÀNH CHO NGƯỜI BÁN</span><h2>Bạn có một cửa hàng muốn giới thiệu?</h2><p>Đăng ký làm người bán và chia sẻ sản phẩm của mình cùng cộng đồng.</p></div><Link to={user?.role === 'admin' ? '/admin' : '/seller'} className="button secondary">{user?.role === 'admin' ? 'Vào trang quản trị' : 'Tìm hiểu Kênh người bán'} <Icon name="arrow" size={18} /></Link></section>
  </>;
}
