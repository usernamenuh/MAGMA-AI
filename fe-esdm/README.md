# ESDM

A React-based application that provides:
- **ChatRAG:** Interactive chat powered by an AI assistant.
- **Scrapping Data:** Web data scraping tool with keyword and limit control.
- **History:** View and manage API call logs with pagination.


---

## 🧩 Tech Stack

| Category        | Technology                  |
|-----------------|-----------------------------|
| UI Framework    | [React 18+](https://react.dev/) |
| Styling         | [Material UI v6+](https://mui.com/) |
| Routing         | [React Router](https://reactrouter.com/) |
| State Handling  | React Hooks (`useState`, `useEffect`) |
| API Integration | Custom `fetchLogs` / `scrapeData` methods |
| Build Tool      | Vite / CRA (depending on setup) |

---

## ⚙️ Setup & Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/TagflowAI/fe-esdm.git
   cd fe-esdm
    ```

2. **Install dependencies**

   ```bash
   npm install
   ```

3. **Set up your API endpoint**

   ```js
   export const API_BASE = "http://localhost:8000";
   ```

4. **Run the app**

   ```bash
   vite
   ```

5. **Open in browser**

   ```
   http://localhost:3000
   ```

---

## Security Check
```bash
npm run security:check:rsc
```