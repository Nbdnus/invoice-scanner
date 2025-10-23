import { useEffect } from "react";

type ToastProps = {
  kind?: "success" | "error" | "info";
  message: string;
  onClose: () => void;
  timeout?: number;
};

export default function Toast({ kind="info", message, onClose, timeout=2500 }: ToastProps) {
  useEffect(() => {
    const id = setTimeout(onClose, timeout);
    return () => clearTimeout(id);
  }, [onClose, timeout]);

  const styles = {
    success: "bg-emerald-600",
    error: "bg-red-600",
    info: "bg-slate-700",
  }[kind];

  return (
    <div className={`fixed bottom-6 right-6 z-50 rounded-xl px-4 py-2 text-white shadow-lg ${styles}`}>
      {message}
    </div>
  );
}
