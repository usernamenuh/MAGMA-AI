import { createTheme, ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { useMemo, useState } from 'react';

export const MuiThemeProvider = ({ children }) => {
  const [mode] = useState('light');

  const theme = useMemo(
    () =>
      createTheme({
        typography: {
          fontFamily: 'Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
          body1: { fontSize: '0.9375rem', lineHeight: 1.6 },
          body2: { fontSize: '0.875rem', lineHeight: 1.55 },
          caption: { fontSize: '0.75rem', lineHeight: 1.5 },
          button: { textTransform: 'none', fontWeight: 600 },
        },
        palette: {
          mode,
          primary: {
            main: '#602A89',
            light: '#8185D5',
          },
          secondary: {
            main: '#FF8600',
          },
          button: {
            main: '#27187E',
          },
        },
      }),
    [mode]
  );

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      {children}
    </ThemeProvider>
  );
};
