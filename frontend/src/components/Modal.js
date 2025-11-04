import "../styling/modal.css";

export default function Modal({ open, onClose, children }) {
  if (!open) return null;

  return (
    <div className="modal-overlay">
      <div className="modal-box">
        {children}
        <button className="modal-close" onClick={onClose}>Close</button>
      </div>
    </div>
  );
}
