// src/pages/Doctor.js
import { useState, useEffect } from "react";
import { API } from "../api/api";
import "../styling/doctor.css";
import { FaUserCircle, FaEye, FaTimes } from "react-icons/fa";
import { ethers } from "ethers";
import { sendTx } from "../pages/TransactionUtils";
import address from "../contractAddress.json";

export function toBytes32(x) {
  if (!x) return "0x" + "0".repeat(64);
  if (typeof x === "string" && x.startsWith("0x")) return x;
  return "0x" + x.toString().padStart(64, "0");
}

export default function Doctor() {
  const doctorAddr = localStorage.getItem("wallet");
  const doctorName = localStorage.getItem("name");
  const CONTRACT_ADDRESS = address.address.toString();

  const [patientName, setPatientName] = useState("");
  const [records, setRecords] = useState([]);
  const [showDropdown, setShowDropdown] = useState(false);

  // -------- Load doctor request list ----------
  const loadRecords = async () => {
    try {
      const res = await API.get(`/doctor/requests?doctor_addr=${doctorAddr}`);
      console.log(res);

      // backend returns list with status
      setRecords(res.data.requests || []);
    } catch (e) {
      console.log("Error fetching doctor requests", e);
    }
  };

  useEffect(() => {
    loadRecords();
  }, []);

  // ---------- Request Access ----------
  const requestAccess = async () => {
    try {
      if (!patientName.trim()) return alert("Enter patient name");

      //------------------------------------------------------------
      // 1) Resolve patient -> get their address + recordId
      //------------------------------------------------------------
      const lookup = await API.get(`/resolve/${patientName.trim()}`);
      const patientAddr = lookup?.data?.patient_address;
      let recordId = lookup?.data?.record_id;
      const idHashuint = lookup?.data?.idHashuint;

      if (!patientAddr || !recordId) {
        alert("❌ Patient not found or no record");
        return;
      }

      recordId = toBytes32(recordId);

      const provider = new ethers.BrowserProvider(window.ethereum);
      const signer = await provider.getSigner();
      const { chainId } = await provider.getNetwork();

      //------------------------------------------------------------
      // 2) Build typed data
      //------------------------------------------------------------
      const role = 0;
      const nonce = Date.now();
      const timestamp = Date.now();
      const ttl = 600_000;

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
        patient: patientAddr,
        recordId,
        role,
        timestamp,
        nonce,
      };

      console.log("Signing typed:", message);

      //------------------------------------------------------------
      // ✅ Sign typed message
      //------------------------------------------------------------
      const signature = await signer.signTypedData(domain, types, message);
      const sig = ethers.Signature.from(signature);

      //------------------------------------------------------------
      // 4) Build form → backend
      //------------------------------------------------------------
      const form = new FormData();
      form.append("doctor_address", doctorAddr);
      form.append("patient_address", patientAddr);
      form.append("record_id", recordId);
      form.append("role", String(role));
      form.append("timestamp", String(timestamp));
      form.append("nonce", String(nonce));

      form.append("sig_v", String(sig.v));
      form.append("sig_r", sig.r);
      form.append("sig_s", sig.s);

      form.append("ttl", String(ttl));

      //------------------------------------------------------------
      // 5) Get transaction data from backend
      //------------------------------------------------------------
      const backend = await API.post("/access-request", form);
      const txData = backend?.data?.tx_data;
      console.log("TX from backend:", txData);

      if (!txData) return alert("❌ No tx from backend");

      //------------------------------------------------------------
      // 6) Send via MetaMask
      //------------------------------------------------------------
      const txHash = await sendTx(txData);
      alert(`✅ Access request submitted\nTx: ${txHash}`);

      loadRecords();
    } catch (err) {
      console.error("❌ requestAccess error:", err);
      if (err.response.status === 400){
        alert("Patient did not give consent");
      }
      else {
        alert("❌ Access request failed — check console");
      }
    }
  };

  // ---------- Cancel ----------
  const cancelRequest = async (patient) => {
    try {
      const form = new FormData();
      form.append("patient_id", patient);
      form.append("doctor_id", doctorAddr);

      await API.post("/cancel", form);
      alert(`🚫 Request cancelled for: ${patient}`);
      loadRecords();
    } catch {
      alert("Error cancelling");
    }
  };

const viewEHR = async (record_id, token) => {
  try {
    const res = await API.get(`/view/${record_id}`, {
      params: { token, doctor: doctorAddr },
      responseType: "blob"
    });
    console.log(res);

    // ✅ Auto-download

    const url = URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));

    // ✅ Open PDF tab
    window.open(url, "_blank");

    setTimeout(() => URL.revokeObjectURL(url), 5000);
  } catch (e) {
    alert("❌ Token invalid or access denied");
  }
};

  const toggleDropdown = () => setShowDropdown((p) => !p);
  const handleLogout = () => {
    localStorage.clear();
    window.location.href = "/";
  };

  return (
    <div className="patient-wrapper">
      <header className="patient-header">
        <div className="left-group">
          <h2 className="app-name">EHRChain</h2>
        </div>

        <div className="right-group">
          <div className="user-info" onClick={toggleDropdown}>
            <FaUserCircle size={26} />
            <span>{doctorName}</span>
          </div>

          {showDropdown && (
            <div className="dropdown-menu">
              <button onClick={handleLogout}>Logout</button>
            </div>
          )}
        </div>
      </header>

      <div className="patient-main">
        <h1>Welcome, Dr. {doctorName}</h1>
        <p>Request access to a patient’s EHR securely.</p>

        <div className="upload-card" style={{ marginBottom: 40 }}>
          <input
            type="text"
            placeholder="Enter Patient Name"
            value={patientName}
            onChange={(e) => setPatientName(e.target.value)}
            className="upload-input"
          />
          <button className="upload-btn" onClick={requestAccess}>
            Request Access
          </button>
        </div>

        <h2>Patient Requests</h2>

        {records.length === 0 ? (
          <p className="no-data">No requests yet ⏳</p>
        ) : (
          <table className="styled-table">
            <thead>
              <tr>
                <th>Patient</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>

            <tbody>
              {records.map((r, i) => (
                <tr key={i}>
                  <td>{r.patient}</td>
                  <td
                    style={{
                      color:
                        r.status === "approved" ? "#21a021" : "#cc7a00",
                      fontWeight: 600,
                      textTransform: "capitalize",
                    }}
                  >
                    {r.status}
                  </td>
                  <td>
                    {r.status === "approved" ? (
                      <FaEye onClick={() => viewEHR(r.record_id, r.token)} disabled={r.status === "expired"}/>
                    ) : (
                      <FaTimes
                        className="cancel-icon"
                        onClick={() => cancelRequest(r.patient)}
                      />
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
