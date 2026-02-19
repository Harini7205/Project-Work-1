import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import "../styling/login.css";
import { isMetaMaskInstalled, requestWalletAccount } from "../web3/connectWallet";
import { sendTx } from "../pages/TransactionUtils";
import { FaUserShield, FaUserMd, FaUserInjured } from "react-icons/fa";

export default function Login() {
  const nav = useNavigate();

  const [email, setEmail] = useState("");
  const [otp, setOtp] = useState("");
  const [role, setRole] = useState(null);
  const [step, setStep] = useState("email"); // email → otp → wallet
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  /* ======================================================
     STEP 1 — REQUEST OTP
  ====================================================== */

  useEffect(() => {
    localStorage.clear();
  }, []);
  
  const requestOtp = async () => {
    if (!email) {
      setMessage("Enter email");
      return;
    }

    setLoading(true);
    try {
      await fetch("http://127.0.0.1:8000/ehr/auth/request-otp", {
        method: "POST",
        body: new URLSearchParams({ email }),
      });
      setStep("otp");
      setMessage("OTP sent to your email");
    } catch {
      setMessage("Failed to send OTP");
    } finally {
      setLoading(false);
    }
  };

  /* ======================================================
     STEP 2 — VERIFY OTP + CONNECT WALLET
  ====================================================== */
  const verifyOtpAndLogin = async () => {
    if (!otp || !role) {
      setMessage("OTP and role required");
      return;
    }

    if (!isMetaMaskInstalled()) {
      window.open("https://metamask.io/download/", "_blank");
      return;
    }

    setLoading(true);

    try {
      const wallet = await requestWalletAccount();
      if (!wallet) {
        setMessage("Unlock MetaMask");
        return;
      }

      const res = await fetch("http://127.0.0.1:8000/ehr/auth/verify-otp", {
        method: "POST",
        body: new URLSearchParams({
          email,
          otp,
          wallet,
          role,
        }),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);

      localStorage.setItem("email", email);
      localStorage.setItem("wallet", wallet);
      localStorage.setItem("role", role);

      /* ---------- Generate ECC keys ---------- */
      const keyResp = await fetch("http://127.0.0.1:8000/ehr/generate-keys", {
        method: "POST",
      });
      const { private_key, public_key } = await keyResp.json();

      localStorage.setItem("priv", private_key);
      localStorage.setItem("pub", public_key);

      /* ---------- Register on-chain (once) ---------- */
      if (!localStorage.getItem("onchain_registered")) {
        const form = new FormData();
        form.append("public_key_hex", public_key);
        form.append("eth_address", wallet);

        const regResp = await fetch("http://127.0.0.1:8000/ehr/register", {
          method: "POST",
          body: form,
        });
        const regData = await regResp.json();

        alert("Confirm blockchain transaction in MetaMask");
        await sendTx(regData.tx_data);

        localStorage.setItem("onchain_registered", "1");
      }

      nav("/" + role);
    } catch (e) {
      console.error(e);
      setMessage("Login failed");
    } finally {
      setLoading(false);
    }
  };

  /* ======================================================
     ADMIN LOGIN (NO WALLET)
  ====================================================== */
  const adminLogin = () => {
    const pwd = prompt("Enter Admin Password");
    if (pwd === "IamAdmin") nav("/admin");
    else alert("Invalid admin password");
  };

  /* ======================================================
     UI
  ====================================================== */
  return (
    <div className="login-page">
      <h1>EHR Access Portal</h1>
      <p className="tagline">Secure Blockchain EHR</p>

      {message && <p className="warning">{message}</p>}

      {/* STEP 1 — EMAIL */}
      {step === "email" && (
        <div className="login-box">
          <input
            type="email"
            placeholder="Enter email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <button onClick={requestOtp} disabled={loading}>
            Send OTP
          </button>
        </div>
      )}

      {/* STEP 2 — OTP + ROLE */}
      {step === "otp" && (
        <>
          <input
            type="text"
            placeholder="Enter OTP"
            value={otp}
            onChange={(e) => setOtp(e.target.value)}
          />

          <div className="role-grid">
            <div onClick={() => setRole("patient")} className="role-box">
              <FaUserInjured />
              <h3>Patient</h3>
            </div>

            <div onClick={() => setRole("doctor")} className="role-box">
              <FaUserMd />
              <h3>Doctor</h3>
            </div>

            <div onClick={adminLogin} className="role-box">
              <FaUserShield />
              <h3>Admin</h3>
            </div>
          </div>

          <button onClick={verifyOtpAndLogin} disabled={loading}>
            Login
          </button>
        </>
      )}
    </div>
  );
}
