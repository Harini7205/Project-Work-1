import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import "../styling/login.css";
import { isMetaMaskInstalled, requestWalletAccount } from "../web3/connectWallet";
import { sendTx } from "../pages/TransactionUtils";
import { FaUserShield, FaUserMd, FaUserInjured } from "react-icons/fa";

export default function Login() {
  const nav = useNavigate();

  const [step, setStep] = useState("role"); // role → email → otp
  const [role, setRole] = useState(null);
  const [email, setEmail] = useState("");
  const [otp, setOtp] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    localStorage.clear();
  }, []);

  /* ======================================================
     STEP 0 — ROLE SELECTION
  ====================================================== */
  const selectRole = (r) => {
    if (r === "admin") {
      const pwd = prompt("Enter Admin Password");
      if (pwd === "IamAdmin") nav("/admin");
      else alert("Invalid admin password");
      return;
    }

    setRole(r);
    setStep("email");
  };

  /* ======================================================
     STEP 1 — REQUEST OTP
  ====================================================== */
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
     STEP 2 — VERIFY OTP → WALLET → LOGIN / REGISTER
  ====================================================== */
  const verifyOtpAndContinue = async () => {
    if (!otp) {
      setMessage("Enter OTP");
      return;
    }

    if (!isMetaMaskInstalled()) {
      window.open("https://metamask.io/download/", "_blank");
      return;
    }

    setLoading(true);

    try {
      // 1️⃣ Verify OTP
      const verifyRes = await fetch(
        "http://127.0.0.1:8000/ehr/auth/verify-otp",
        {
          method: "POST",
          body: new URLSearchParams({ email, otp }),
        }
      );

      const verifyData = await verifyRes.json();
      if (!verifyRes.ok) throw new Error(verifyData.detail);

      // 2️⃣ Connect wallet
      const wallet = await requestWalletAccount();
      if (!wallet) throw new Error("Wallet not connected");

      localStorage.setItem("email", email);
      localStorage.setItem("wallet", wallet);
      localStorage.setItem("role", role);

      // 3️⃣ Try login
      const loginRes = await fetch(
        "http://127.0.0.1:8000/ehr/auth/login",
        {
          method: "POST",
          body: new URLSearchParams({
            email,
            wallet,
            role,
          }),
        }
      );

      // 4️⃣ If user not found → register
      if (loginRes.status === 401) {
        const regRes = await fetch(
          "http://127.0.0.1:8000/ehr/auth/register",
          {
            method: "POST",
            body: new URLSearchParams({
              email,
              wallet,
              role,
            }),
          }
        );

        if (!regRes.ok) throw new Error("Registration failed");
      }

      else if (loginRes.status == 400){
        throw new Error("Invalid role selected. Please select the correct role.");
      }

      // 5️⃣ Generate ECC keys (local)
      const keyResp = await fetch("http://127.0.0.1:8000/ehr/generate-keys", {
        method: "POST",
      });
      const { private_key, public_key } = await keyResp.json();

      localStorage.setItem("priv", private_key);
      localStorage.setItem("pub", public_key);

      // Check on-chain registration FIRST
const check = await fetch(
  `http://127.0.0.1:8000/ehr/identity/registered?wallet=${wallet}`
);
const { registered } = await check.json();

if (!registered) {
  // Only register if NOT already registered
  const form = new FormData();
  form.append("public_key_hex", public_key);
  form.append("eth_address", wallet);

  const regResp = await fetch(
    "http://127.0.0.1:8000/ehr/register",
    {
      method: "POST",
      body: form,
    }
  );

  const regData = await regResp.json();

  alert("Confirm blockchain transaction in MetaMask");
  await sendTx(regData.tx_data);
}
      nav("/" + role);
    } catch (e) {
      console.error(e);
      setMessage(e.message || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  /* ======================================================
     UI
  ====================================================== */
  return (
    <div className="login-page">
      <h1>EHR Access Portal</h1>
      <p className="tagline">Secure Blockchain EHR</p>

      {message && <p className="warning">{message}</p>}

      {/* STEP 0 — ROLE */}
      {step === "role" && (
        <div className="role-grid">
          <div onClick={() => selectRole("patient")} className="role-box">
            <FaUserInjured />
            <h3>Patient</h3>
          </div>

          <div onClick={() => selectRole("doctor")} className="role-box">
            <FaUserMd />
            <h3>Doctor</h3>
          </div>

          <div onClick={() => selectRole("admin")} className="role-box">
            <FaUserShield />
            <h3>Admin</h3>
          </div>
        </div>
      )}

      {/* STEP 1 — EMAIL */}
      {step === "email" && (
        <div className="login-box">
          <input
            type="email"
            placeholder={`Enter ${role} email`}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <button onClick={requestOtp} disabled={loading}>
            Send OTP
          </button>
        </div>
      )}

      {/* STEP 2 — OTP */}
      {step === "otp" && (
        <div className="login-box">
          <input
            type="text"
            placeholder="Enter OTP"
            value={otp}
            onChange={(e) => setOtp(e.target.value)}
          />
          <button onClick={verifyOtpAndContinue} disabled={loading}>
            Continue
          </button>
        </div>
      )}
    </div>
  );
}