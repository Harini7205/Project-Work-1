import { useState } from "react";
import { API } from "../api/api";

export default function Doctor() {
  const [doctor, setDoctor] = useState("");
  const [patient, setPatient] = useState("");

  const req = async () => {
    const form = new FormData();
    form.append("doctor_addr", doctor);
    form.append("patient_id", patient);
    const res = await API.post("/access-request", form);
    alert(JSON.stringify(res.data));
  };

  return (
    <div>
      <h1>Doctor Dashboard</h1>

      <input
        placeholder="Doctor Address"
        value={doctor}
        onChange={(e) => setDoctor(e.target.value)}
      />

      <input
        placeholder="Patient ID"
        value={patient}
        onChange={(e) => setPatient(e.target.value)}
      />

      <button onClick={req}>Request Access</button>
    </div>
  );
}
