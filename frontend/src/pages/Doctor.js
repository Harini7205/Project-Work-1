// src/pages/Doctor.jsx
import { useState, useEffect } from "react";
import { API } from "../api/api";
import "../styling/doctor.css";
import { FaUserCircle, FaEye, FaTimes } from "react-icons/fa";
import { ethers } from "ethers";
import { sendTx } from "./TransactionUtils";
import address from "../contractAddress.json";

export function toBytes32(x) {
  if (!x) return "0x" + "0".repeat(64);
  if (typeof x === "string" && x.startsWith("0x")) return x;
  return "0x" + String(x).padStart(64, "0");
}

export default function Doctor() {
  const doctorAddr = localStorage.getItem("wallet");
  const doctorName = localStorage.getItem("name");
  const CONTRACT_ADDRESS = address.address.toString();

  const [patientId, setPatientId] = useState("");
  const [records, setRecords] = useState([]);
  const [showDropdown, setShowDropdown] = useState(false);

  /* ---------------- LOAD DOCTOR REQUESTS ---------------- */
  const loadRecords = async () => {
    try {
      const res = await API.get(`/requests/doctor?wallet=${doctorAddr}`);
      setRecords(res.data || []);
    } catch (e) {
      console.error("Error fetching doctor requests", e);
      setRecords([]);
    }
  };

  useEffect(() => {
    loadRecords();
  }, []);

  /* ---------------- REQUEST ACCESS ---------------- */
  const requestAccess = async () => {
    if (!patientId) return alert("Enter Patient ID");

    try {
      // 1️⃣ Resolve patient record and consent
      const resolve = await API.get(`/resolve-patient/${patientId}`);
      const { patient_address, record_id, patient_view, consent } = resolve.data;

      if (!consent) return alert("Patient has not given consent yet");

      const provider = new ethers.BrowserProvider(window.ethereum);
      const signer = await provider.getSigner();
      const { chainId } = await provider.getNetwork();

      const role = 0;
      const nonce = Date.now();
      const timestamp = Date.now();
      const ttl = 600;

      const domain = {
        name: "AccessRegistry",
        version: "1",
        chainId: Number(chainId),
        verifyingContract: CONTRACT_ADDRESS,
      };

      const types = {
        AccessRequest: [
          { name: "provider", type: "address" },
          { name: "patient", type: "address" },
          { name: "recordId", type: "bytes32" },
          { name: "role", type: "uint8" },
          { name: "timestamp", type: "uint64" },
          { name: "nonce", type: "uint256" },
        ],
      };

      const message = {
        provider: doctorAddr,
        patient: patient_address,
        recordId: toBytes32(record_id),
        role,
        timestamp,
        nonce,
      };

      alert("Sign access request (no gas)");

      const signature = await signer.signTypedData(domain, types, message);
      const sig = ethers.Signature.from(signature);

      // 2️⃣ Send to backend
      const form = new FormData();
      form.append("doctor_address", doctorAddr);
      form.append("patient_id", patientId);
      form.append("record_id", record_id);
      form.append("role", role);
      form.append("timestamp", timestamp);
      form.append("nonce", nonce);
      form.append("sig_v", sig.v);
      form.append("sig_r", sig.r);
      form.append("sig_s", sig.s);
      form.append("ttl", ttl);

      const backend = await API.post("/access-request", form);
      const txData = backend.data.tx_data;

      alert("Confirm blockchain tx (gas required)");
      await sendTx(txData);

      alert("✅ Access request submitted");
      loadRecords();
    } catch (e) {
      console.error(e);
      alert("❌ Access request failed");
    }
  };

  /* ---------------- VIEW EHR ---------------- */
  const viewEHR = async (record_id, token) => {
    try {
      const res = await API.get(`/view/${record_id}`, { params: { token }, responseType: "blob" });
      const url = URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
      window.open(url, "_blank");
      setTimeout(() => URL.revokeObjectURL(url), 5000);
    } catch {
      alert("Token invalid or expired");
    }
  };

  /* ---------------- UI HELPERS ---------------- */
  const toggleDropdown = () => setShowDropdown((p) => !p);
  const handleLogout = () => {
    localStorage.clear();
    window.location.href = "/";
  };

  return (
    <div className="doctor-wrapper">
      <header className="doctor-header">
        <h2 className="app-name">EHRChain</h2>

        <div className="user-info" onClick={toggleDropdown}>
          <FaUserCircle size={26} />
          <span>{doctorName}</span>
        </div>

        {showDropdown && (
          <div className="dropdown-menu">
            <button onClick={handleLogout}>Logout</button>
          </div>
        )}
      </header>

      <div className="doctor-main">
        <h1>Welcome, Dr. {doctorName}</h1>
        <p>Request access to a patient’s EHR securely.</p>

        {/* -------- REQUEST ACCESS -------- */}
        <div className="upload-card" style={{ marginBottom: 40 }}>
          <input
            type="text"
            placeholder="Enter Patient ID"
            value={patientId}
            onChange={(e) => setPatientId(e.target.value)}
            className="upload-input"
          />
          <button className="upload-btn" onClick={requestAccess}>
            Request Access
          </button>
        </div>

        {/* -------- REQUEST LIST -------- */}
        <h2>My Access Requests</h2>

        {records.length === 0 ? (
          <p className="no-data">No requests yet ⏳</p>
        ) : (
          <table className="records-table">
            <thead>
              <tr>
                <th>Patient ID</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>

            <tbody>
              {records.map((r, i) => (
                <tr key={i}>
                  <td>{r.patient_id}</td>
                  <td
                    style={{
                      color: r.status === "approved" ? "#21a021" : "#cc7a00",
                      fontWeight: 600,
                      textTransform: "capitalize",
                    }}
                  >
                    {r.status}
                  </td>
                  <td>
                    {r.status === "approved" && (
                      <FaEye
                        onClick={() => viewEHR(r.record_id, r.token)}
                        style={{ cursor: "pointer" }}
                      />
                    )}
                    {r.status === "expired" && (
                      <FaTimes style={{ color: "#cc0000", cursor: "not-allowed" }} />
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
