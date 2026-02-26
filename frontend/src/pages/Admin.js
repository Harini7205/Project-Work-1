import { useState, useEffect } from "react";
import { API } from "../api/api";
import "../styling/admin.css";
import { sendTx } from "./TransactionUtils";

export default function Admin() {

  const [wallet, setWallet] = useState(localStorage.getItem("wallet"));
  const [pub, setPub] = useState(localStorage.getItem("pub"));

  const [file, setFile] = useState(null);
  const [encBlob, setEncBlob] = useState(null);

  const [cid, setCid] = useState("");
  const [ch, setCh] = useState("");
  const [recordId, setRecordId] = useState("");

  const [step, setStep] = useState(1);

  const [patients, setPatients] = useState([]);
  const [showPatients, setShowPatients] = useState(false);

  /* AUTO KEY GENERATION */
  useEffect(() => {
    const generateKeys = async () => {
      if (!pub) {
        try {
          const res = await fetch("http://127.0.0.1:8000/ehr/generate-keys", {
            method: "POST",
          });

          const data = await res.json();

          localStorage.setItem("pub", data.public_key);
          localStorage.setItem("priv", data.private_key);

          setPub(data.public_key);
        } catch {
          alert("Key generation failed");
        }
      }
    };

    generateKeys();
  }, [pub]);

  /* CONNECT WALLET */
  const connectWallet = async () => {
    if (!window.ethereum) {
      alert("Install MetaMask");
      return null;
    }

    const accounts = await window.ethereum.request({
      method: "eth_requestAccounts",
    });

    const address = accounts[0];
    localStorage.setItem("wallet", address);
    setWallet(address);

    return address;
  };

  /* STEP 1 ENCRYPT */
  const doEncrypt = async () => {
    if (!file) return alert("Choose file");

    const form = new FormData();
    form.append("file", file);

    const res = await API.post("/encrypt", form, {
      responseType: "blob",
    });

    setEncBlob(new Blob([res.data]));
    setStep(2);
  };

  /* STEP 2 UPLOAD */
  const doUpload = async () => {
    const form = new FormData();
    form.append("file", encBlob, "encrypted.bin");

    const res = await API.post("/ipfs-upload", form);

    setCid(res.data.cid);
    setStep(3);
  };

  /* STEP 3 HASH */
  const doHash = async () => {
    const form = new FormData();
    form.append("public_key_hex", pub);

    const res = await API.post(`/chameleon-hash/${cid}`, form);

    setCh(res.data.ch);
    setStep(4);
  };

  /* STEP 4 STORE */
  const doStore = async () => {

    let currentWallet = wallet;

    if (!currentWallet) {
      currentWallet = await connectWallet();
      if (!currentWallet) return;
    }

    const form = new FormData();
    form.append("cid", cid);
    form.append("ch", ch);
    form.append("eth_address", currentWallet);

    const res = await API.post("/store-record", form);

    setRecordId(res.data.record_id);

    await sendTx(res.data.tx_data);

    setStep(5);
  };

  /* LOAD PATIENTS */
  const loadPatients = async () => {
    try {
      const res = await API.get("/patients");
      setPatients(res.data);
      setShowPatients(true);
    } catch (err) {
      console.log(err);
      alert("Failed to load patients. Check backend.");
    }
  };

  const logout = () => {
    localStorage.clear();
    window.location.href = "/";
  };

  return (
    <div>

      {/* HEADER */}
      <div className="admin-header">
        <h1>Admin Dashboard</h1>
        <button className="logout-btn" onClick={logout}>
          Logout
        </button>
      </div>


      {/* PATIENT TABLE */}
      {showPatients && (
        <div className="patient-table">
          <table>
            <thead>
              <tr>
                <th>Patient ID</th>
                <th>Record ID</th>
                <th>Access</th>
              </tr>
            </thead>
            <tbody>
              {patients.map((p, i) => (
                <tr key={i}>
                  <td>{p.patient_id}</td>
                  <td>{p.record_id}</td>
                  <td>
                    <button>
                      View Access
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* CENTER CARD */}
      <div className="center-box">

        {/* ENCRYPT */}
        {step === 1 && (
          <div className="box">
            <h2>Encrypt EHR</h2>

            <input
              type="file"
              onChange={(e) => setFile(e.target.files[0])}
            />

            <button onClick={doEncrypt}>
              Encrypt
            </button>
          </div>
        )}

        {/* UPLOAD */}
        {step === 2 && (
          <div className="box">
            <h2>Upload to IPFS</h2>

            <button onClick={doUpload}>
              Upload File
            </button>
          </div>
        )}

        {/* CID SHOW */}
        {step === 3 && (
          <div className="box">
            <h2>File Uploaded</h2>

            <div className="info-block">
              <label>CID</label>
              <div className="value-box">
                {cid}
              </div>
            </div>

            <button onClick={doHash}>
              Compute Chameleon Hash
            </button>
          </div>
        )}

        {/* HASH SHOW */}
        {step === 4 && (
          <div className="box">
            <h2>Hash Generated</h2>

            <div className="info-block">
              <label>CID</label>
              <div className="value-box">
                {cid}
              </div>
            </div>

            <div className="info-block">
              <label>Chameleon Hash</label>
              <div className="value-box">
                {ch}
              </div>
            </div>

            <button onClick={doStore}>
              Store on Blockchain
            </button>
          </div>
        )}

        {/* RECORD */}
        {step === 5 && (
          <div className="box">
            <h2>Record Stored Successfully</h2>

            <div className="info-block">
              <label>Record ID</label>
              <div className="value-box">
                {recordId}
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
