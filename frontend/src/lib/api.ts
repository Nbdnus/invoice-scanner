import axios from "axios";
const api = axios.create({ baseURL: "/api" }); // <— wichtig
export default api;
