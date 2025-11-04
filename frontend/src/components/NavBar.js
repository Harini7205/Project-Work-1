import "../styling/navbar.css";
import { Link } from "react-router-dom";

export default function Navbar() {
  return (
    <nav className="nav">
      <h2 className="logo">EHR-Chain</h2>

      <div className="nav-links">
        <Link to="/">Home</Link>
        <Link to="/patient">Patient</Link>
        <Link to="/doctor">Doctor</Link>
        <Link to="/admin">Admin</Link>
      </div>
    </nav>
  );
}
