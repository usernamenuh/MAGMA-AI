import { useState } from "react";
import {
    Box,
    Button,
    Container,
    Grid,
    Typography,
    Stack, 
    OutlinedInput, 
    InputAdornment, 
    IconButton, 
    FormControl,
} from "@mui/material";
import { useAuth } from "@/hooks/useAuth.jsx";
import { useNavigate } from "react-router-dom";
import { CHAT, REGISTER } from "@/utils/routes.jsx";
import logo from "../assets/logo-esdm.png";
import VisibilityOffIcon from "@mui/icons-material/VisibilityOff";
import VisibilityIcon from "@mui/icons-material/Visibility";

export default function LoginPage() {
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const { error, setError, login, loading } = useAuth();
    const navigate = useNavigate();
    const [showPassword, setShowPassword] = useState(false);
    const handleSubmit = async (e) => {
        e.preventDefault();
        setError("");

        if (!email || !password) {
            setError("⚠️ Please enter both email and password");
            return;
        }

        const result = await login(email, password);
        console.log(result);
        if (!result) {
            // the login() already set the correct error message
            return;
        }

        navigate(CHAT);
    };



    return (
        <Container
            maxWidth={false}
            disableGutters
            sx={{
                width: "100%",
                height: "100vh",
                bgcolor: "#ffffff",
                display: "flex",
                flexDirection: "column",
                justifyContent: "center",
                alignItems: "center",
                py: 4,
            }}
        >

        <Box textAlign="center" mb={2}>
                <Box component="img" src={logo} alt="Logo" sx={{ width: 150, mb: 1 }} />
                <Typography variant="h6" sx={{ color: "#000000", fontWeight: 600 }}>
                    Kementerian ESDM
                </Typography>
            </Box>

            <Grid container spacing={3} justifyContent="center" alignItems="center">
                <Grid item xs={12} md={12}>

                    <Box component="form" onSubmit={handleSubmit}>
                        <FormControl fullWidth margin="normal" variant="outlined">
                            <OutlinedInput
                                type="text"
                                placeholder="Enter Your Username"
                                fullWidth
                                margin="normal"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                sx={{
                                    bgcolor: "#ffffff",
                                    color: "#E1E6EB",
                                    borderRadius: 4,
                                    "& input": {
                                        backgroundColor: "#ffffff",
                                        color: "#E1E6EB",
                                    },
                                    "& input:-webkit-autofill": {
                                        WebkitBoxShadow: "0 0 0 1000px #000000 inset",
                                        WebkitTextFillColor: "#E1E6EB",
                                    },
                                    "& .MuiOutlinedInput-notchedOutline": {
                                        borderColor: "#737373ff",
                                    },
                                    "&:hover .MuiOutlinedInput-notchedOutline": {
                                        borderColor: "#000000",
                                    },
                                    "&.Mui-focused .MuiOutlinedInput-notchedOutline": {
                                        borderColor: "#000000",
                                    },
                                    input: { color: "#3b3b3bff" },
                                }}
                            />
                        </FormControl>

                        <FormControl fullWidth margin="normal" variant="outlined">
                            <OutlinedInput
                                id="password"
                                placeholder="Enter Your Password"
                                type={showPassword ? "text" : "password"}
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                sx={{
                                    bgcolor: "#ffffff",
                                    color: "#E1E6EB",
                                    borderRadius: 4,
                                    "& input": {
                                        backgroundColor: "#ffffff",
                                        color: "#3b3b3bff",
                                    },
                                    "& input:-webkit-autofill": {
                                        WebkitBoxShadow: "0 0 0 1000px #000000 inset",
                                        WebkitTextFillColor: "#E1E6EB",
                                    },
                                    "& .MuiOutlinedInput-notchedOutline": {
                                        borderColor: "#737373ff",
                                    },
                                    "&:hover .MuiOutlinedInput-notchedOutline": {
                                        borderColor: "#000000",
                                    },
                                    "&.Mui-focused .MuiOutlinedInput-notchedOutline": {
                                        borderColor: "#000000",
                                    },
                                    input: { color: "#3b3b3bff" },
                                }}
                                endAdornment={
                                    <InputAdornment position="end">
                                        <IconButton
                                            onClick={() => setShowPassword(!showPassword)}
                                            edge="end"
                                            sx={{ color: "#3b3b3bff" }}
                                        >
                                            {showPassword ? <VisibilityOffIcon /> : <VisibilityIcon />}
                                        </IconButton>
                                    </InputAdornment>
                                }
                            />
                        </FormControl>

                        {error && (
                            <Typography color="error" variant="body2" mt={1}>
                                {error}
                            </Typography>
                        )}

                        <Button
                            type="submit"
                            variant="contained"
                            fullWidth
                            sx={{
                                mt: 2,
                                backgroundColor: "#FFF500",
                                color: "#000000",
                                borderRadius: "8px",
                                fontWeight: 600,
                                "&:hover": {
                                    backgroundColor: "rgba(255,245,0,0.82)",
                                },
                                textTransform: "none",
                                textDecoration: "none",
                            }}
                            disabled={loading}
                        >
                            {loading ? "Logging in..." : "Login"}
                        </Button>
                    </Box>
                </Grid>
            </Grid>

            {/*<Box display="flex" justifyContent="center" mt={2}>*/}
            {/*    <Button*/}
            {/*        variant="text"*/}
            {/*        onClick={() => navigate(FORGOT_PASSWORD)}*/}
            {/*        sx={{ fontWeight: "medium", color: "#FFF500", textTransform: "none",  }}*/}
            {/*    >*/}
            {/*        Forgot password?*/}
            {/*    </Button>*/}
            {/*</Box>*/}

            <Grid item xs={12} md={12}>
                <Stack
                    direction="row"
                    spacing={1}
                    justifyContent="center"
                    alignItems="center"
                    pt={2}
                >
                    <Typography variant="body1" sx={{ color: "#5c5c5cff" }}>
                        Don’t have an account?
                    </Typography>
                    
                    <Typography
                        variant="body1"
                        onClick={() => window.open("http://172.16.2.228:8086/register", "_blank")}
                        sx={{ fontWeight: "bold", color: "#000000", "&:hover": { cursor: "pointer", textDecoration: "underline" } }}
                    >
                        Register
                    </Typography>
                </Stack>
            </Grid>
        </Container>
    );
}
