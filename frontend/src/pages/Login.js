import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import "../styling/login.css";
import { isMetaMaskInstalled, requestWalletAccount } from "../web3/connectWallet";
import {
  FaUserShield,
  FaUserMd,
  FaUserInjured
} from "react-icons/fa";

export default function Login() {
  const nav = useNavigate();

  const [message, setMessage] = useState("");
  const [userName, setUserName] = useState("");
  const [showRoles, setShowRoles] = useState(false);

  const [showMetaMaskInfo, setShowMetaMaskInfo] = useState(false);
  const [rolePending, setRolePending] = useState(null);

  useEffect(() => {
    // Ensure fresh login every time
    localStorage.removeItem("wallet");
    localStorage.removeItem("role");
    localStorage.removeItem("name");
  }, []);

  // Step 1 — Next button
  const handleNext = () => {
    if (!userName.trim()) {
      setMessage("⚠️ Please enter your name first.");
      return;
    }
    setShowRoles(true);
    setMessage(""); // clear previous messages
  };

  // Step 2 — click role → ask MetaMask confirmation
  const askPermissionBeforeConnect = (role) => {
    setRolePending(role);
    setShowMetaMaskInfo(true);
  };

  // Step 3 — user approves → connect MetaMask
  const handleMetaMaskProceed = async () => {
    setShowMetaMaskInfo(false);

    const role = rolePending;
    if (!role) return;

    if (!isMetaMaskInstalled()) {
      setMessage("⚠️ MetaMask not detected. Redirecting to install page.");
      window.open("https://metamask.io/download/", "_blank");
      return;
    }

    const address = await requestWalletAccount();
    if (!address) {
      setMessage("⚠️ Unlock or create MetaMask wallet first.");
      return;
    }

    localStorage.setItem("wallet", address);
    localStorage.setItem("role", role);
    localStorage.setItem("name", userName);

    // Register user
    const response = await fetch("http://127.0.0.1:8000/ehr/register", {
      method: "POST",
      body: new URLSearchParams({ name: address }),
    });

    if (response.status === 200 || response.status === 400) {
      nav("/" + role);
    } else {
      setMessage("⚠️ Could not authenticate. Try again.");
    }
  };

  return (
    <div className="login-page">
      <h1>EHR Access Portal</h1>
      <p className="tagline">Blockchain-secured Electronic Health Record Management</p>

      {message && <p className="warning">{message}</p>}

      {/* ✅ Name input */}
      {!showRoles && (
        <div className="name-input-container">
          <label>Your Name</label>
          <input
            type="text"
            placeholder="Enter full name"
            value={userName}
            onChange={(e) => setUserName(e.target.value)}
          />
          <button className="next-btn" onClick={handleNext}>
            Next →
          </button>
        </div>
      )}

      {/* ✅ Role selection after Next */}
      {showRoles && (
        <>
          <p className="select-role">Select your role</p>

          <div className="role-grid">

            {/* ✅ Patient */}
            <div
              onClick={() => askPermissionBeforeConnect("patient")}
              className="role-box"
            >
              <FaUserInjured className="role-icon" />
              <h3>Patient</h3>
              <p>Upload, update & manage your EHR</p>
            </div>

            {/* ✅ Doctor */}
            <div
              onClick={() => askPermissionBeforeConnect("doctor")}
              className="role-box"
            >
              <FaUserMd className="role-icon" />
              <h3>Doctor</h3>
              <p>Request access to patient records</p>
            </div>

            {/* ✅ Admin */}
            <div
              onClick={() => {
                const key = prompt("Enter Admin Secret:");
                if (key === "IamAdmin") {
                  localStorage.setItem("name", userName);
                  nav("/admin");
                } else {
                  alert("❌ Invalid Admin Secret");
                }
              }}
              className="role-box"
            >
              <FaUserShield className="role-icon" />
              <h3>Admin</h3>
              <p>View blockchain record history</p>
            </div>

          </div>
        </>
      )}

      {/* ✅ MetaMask info modal */}
      {showMetaMaskInfo && (
        <div className="modal-overlay">
          <div className="modal-content">
            <h2 className="modal-title">Before You Continue</h2>
            <p>
              You will now be asked to connect to <b>MetaMask</b>.
              <br /><br />
              MetaMask is a safe testing wallet used here to assign a temporary account
              with <b>test ETH</b>.  
              <br /><br />
            </p>
            <ul className="bullet-points">
            <li>✅ No real money involved</li>
            <li>✅ Safe & reversible</li>
            <li>✅ Required only to authenticate securely</li>
            </ul>

            <div className="modal-btn-row">
              <button
                onClick={() => setShowMetaMaskInfo(false)}
                className="btn-cancel"
              >
                Cancel
              </button>

              <button
                onClick={handleMetaMaskProceed}
                className="btn-confirm"
              >
                Continue
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
