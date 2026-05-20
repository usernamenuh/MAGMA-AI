import { useMediaQuery } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { createContext, useContext, useEffect, useState } from "react";

const noop = () => {};

const AppContext = createContext({
  open: true,
  mobile: false,
  toggleOpen: noop,
});

// eslint-disable-next-line react-refresh/only-export-components
export const useApp = () => useContext(AppContext);

export const AppProvider = ({ children }) => {
  const [open, setOpen] = useState(true);
  const theme = useTheme();
  const mobile = useMediaQuery(theme.breakpoints.down("md"));

  useEffect(() => {
    if (mobile) {
      setOpen(false);
    } else {
      setOpen(true);
    }
  }, [mobile]);

  const toggleOpen = () => setOpen(prev => !prev);

  return (
      <AppContext.Provider value={{ open, mobile, toggleOpen }}>
        {children}
      </AppContext.Provider>
  );
};

export default AppProvider;
