import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

import { useAuth } from "./auth";
import type { Product } from "./api";

export interface CartLine {
  productId: number;
  quantity: number;
}

const KEY_PREFIX = "microshop.cart.v1.";
const MAX_QUANTITY = 99;

function readCart(key: string): CartLine[] {
  try {
    const value: unknown = JSON.parse(localStorage.getItem(key) || "[]");
    if (!Array.isArray(value)) return [];
    const seen = new Set<number>();
    return value.filter((item): item is CartLine => {
      if (!item || typeof item !== "object") return false;
      const line = item as Partial<CartLine>;
      if (
        !Number.isSafeInteger(line.productId) ||
        (line.productId ?? 0) <= 0 ||
        !Number.isInteger(line.quantity) ||
        (line.quantity ?? 0) < 1 ||
        (line.quantity ?? 0) > MAX_QUANTITY ||
        seen.has(line.productId!)
      )
        return false;
      seen.add(line.productId!);
      return true;
    });
  } catch {
    return [];
  }
}

interface CartState {
  lines: CartLine[];
  count: number;
  add: (product: Product, quantity?: number) => void;
  update: (productId: number, quantity: number) => void;
  remove: (productId: number) => void;
}

const CartContext = createContext<CartState | null>(null);

export function CartProvider({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  const key = `${KEY_PREFIX}${user ? `user-${user.id}` : "guest"}`;
  const [, setRevision] = useState(0);
  const lines: CartLine[] = loading ? [] : readCart(key);
  useEffect(() => {
    const sync = (event: StorageEvent) => {
      if (event.key === key) setRevision((value) => value + 1);
    };
    window.addEventListener("storage", sync);
    return () => window.removeEventListener("storage", sync);
  }, [key]);

  const save = useCallback(
    (next: CartLine[]) => {
      try {
        localStorage.setItem(key, JSON.stringify(next));
      } catch {
        throw new Error(
          "Không lưu được giỏ hàng trên trình duyệt. Hãy kiểm tra dung lượng lưu trữ.",
        );
      }
      setRevision((value) => value + 1);
    },
    [key],
  );

  const add = (product: Product, quantity = 1) => {
    if (loading) throw new Error("Đang tải tài khoản, vui lòng thử lại.");
    if (product.status !== "active" || product.quantity < 1)
      throw new Error("Sản phẩm hiện không thể thêm vào giỏ.");
    const previous =
      lines.find((line) => line.productId === product.id)?.quantity ?? 0;
    const next = previous + quantity;
    if (
      !Number.isInteger(quantity) ||
      quantity < 1 ||
      next > MAX_QUANTITY ||
      next > product.quantity
    )
      throw new Error("Số lượng trong giỏ vượt quá tồn kho hiện tại.");
    save([
      ...lines.filter((line) => line.productId !== product.id),
      { productId: product.id, quantity: next },
    ]);
  };

  const update = (productId: number, quantity: number) => {
    if (!Number.isInteger(quantity) || quantity < 1 || quantity > MAX_QUANTITY)
      throw new Error("Số lượng phải từ 1 đến 99.");
    save(
      lines.map((line) =>
        line.productId === productId ? { ...line, quantity } : line,
      ),
    );
  };

  const remove = (productId: number) =>
    save(lines.filter((line) => line.productId !== productId));

  return (
    <CartContext.Provider
      value={{
        lines,
        count: lines.reduce((sum, item) => sum + item.quantity, 0),
        add,
        update,
        remove,
      }}
    >
      {children}
    </CartContext.Provider>
  );
}

export function useCart() {
  const context = useContext(CartContext);
  if (!context) throw new Error("CartProvider is required");
  return context;
}
