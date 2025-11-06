import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import "../styling/login.css";
import { isMetaMaskInstalled, requestWalletAccount } from "../web3/connectWallet";
import { sendTx } from "../pages/TransactionUtils";
import { FaUserShield, FaUserMd, FaUserInjured } from "react-icons/fa";

export default function Login() {
  const nav = useNavigate();

  const [message, setMessage] = useState("");
  const [userName, setUserName] = useState(localStorage.getItem("name") || "");
  const [showRoles, setShowRoles] = useState(false);
  const [showMetaMaskInfo, setShowMetaMaskInfo] = useState(false);
  const [rolePending, setRolePending] = useState(null);

  // Clear role only if user reloads fresh login
  useEffect(() => {
  console.log("LocalStorage values:", {
    wallet: localStorage.getItem("wallet"),
    role: localStorage.getItem("role"),
    name: localStorage.getItem("name"),
  });
}, []);


  // Proceed to role selection ONLY if name is available
  const handleNext = () => {
    if (!userName.trim()) {
      setMessage("⚠️ Please enter your name first.");
      return;
    }

    localStorage.setItem("name", userName);
    setShowRoles(true);
    setMessage("");
  };

  // User clicked a role
  const askPermissionBeforeConnect = (role) => {
    // Check if role already exists
    const savedRole = localStorage.getItem("role");
    if (savedRole && savedRole !== role) {
      setMessage(
        `⚠️ This wallet is already registered as '${savedRole}'. You cannot register as '${role}'.`
      );
      return;
    }

    setRolePending(role);
    setShowMetaMaskInfo(true);
  };

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

    const savedRole = localStorage.getItem("role");
    if (savedRole && savedRole !== role) {
      setMessage(
        `⚠️ This wallet is already registered as '${savedRole}'. You cannot register as '${role}'.`
      );
      return;
    }

    // Save wallet + role
    localStorage.setItem("wallet", address);
    localStorage.setItem("role", role);

    // ✅ Step 1 — Generate ECC keys
    const keyResp = await fetch("http://127.0.0.1:8000/ehr/generate-keys", {
      method: "POST",
    });
    const { private_key, public_key } = await keyResp.json();
    alert("✅ Private and public keys generated");

    localStorage.setItem("priv", private_key);
    localStorage.setItem("pub", public_key);

    // ✅ Step 2 — Register
    const regForm = new FormData();
    regForm.append("public_key_hex", public_key);
    regForm.append("eth_address", address);
    regForm.append("name", userName);

    const regResp = await fetch("http://127.0.0.1:8000/ehr/register", {
      method: "POST",
      body: regForm,
    });
    const data = await regResp.json();

    // ✅ Step 3 — MetaMask TX
    try {
      if (data.tx_data) {
        const txHash = await sendTx(data.tx_data);
        console.log("✅ Registered on-chain:", txHash);
      } else {
        console.warn("No tx_data returned (maybe already registered)");
      }
    } catch (err) {
      console.error(err);
      setMessage("⚠️ On-chain registration failed");
      return;
    }
    alert(`Public key registered on-chain using wallet address ${address}`);

    nav("/" + role);
  };

  return (
    <div className="login-page">
      <h1>EHR Access Portal</h1>
      <p className="tagline">Blockchain-secured Electronic Health Record Management</p>

      {message && <p className="warning">{message}</p>}

      {/* Ask name only if missing */}
      {!showRoles && !localStorage.getItem("name") && (
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

      {/* If name already stored → skip Next */}
      {!showRoles && localStorage.getItem("name") && (
        <>
          <p className="tagline">Welcome back, <b>{localStorage.getItem("name")}</b></p>
          <button className="next-btn" onClick={() => setShowRoles(true)}>
            Continue →
          </button>
        </>
      )}

      {/* Role selection */}
      {showRoles && (
        <>
          <p className="select-role">Select your role</p>
          <div className="role-grid">
            <div onClick={() => askPermissionBeforeConnect("patient")} className="role-box">
              <FaUserInjured className="role-icon" />
              <h3>Patient</h3>
              <p>Upload, update & manage your EHR</p>
            </div>

            <div onClick={() => askPermissionBeforeConnect("doctor")} className="role-box">
              <FaUserMd className="role-icon" />
              <h3>Doctor</h3>
              <p>Request access to patient records</p>
            </div>

            <div
              onClick={() => {
                const role=localStorage.getItem("role");
                if (role && role !== "admin") {
                  alert("Cannot login user as admin");
                  return;
                }
                const key = prompt("Enter Admin Secret:");
                if (key === "IamAdmin") {
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

      {/* MetaMask warning modal */}
      {showMetaMaskInfo && (
        <div className="modal-overlay">
          <div className="modal-content">
            <h2 className="modal-title">Before You Continue</h2>
            <p>
              You will now be asked to connect to <b>MetaMask</b>.
              <br /><br />
              Test ETH will be used — no real money.
            </p>

            <div className="modal-btn-row">
              <button onClick={() => setShowMetaMaskInfo(false)} className="btn-cancel">
                Cancel
              </button>

              <button onClick={handleMetaMaskProceed} className="btn-confirm">
                Continue
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
