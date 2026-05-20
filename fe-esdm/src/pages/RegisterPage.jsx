import { useState } from "react";
import {
    Box,
    Button,
    Container,
    Grid,
    TextField,
    Typography,
    Paper,
    Stack, FormControlLabel, Checkbox, OutlinedInput, IconButton, InputAdornment, FormControl, InputLabel,
} from "@mui/material";
import { useAuth } from "@/hooks/useAuth.jsx";
import { useNavigate } from "react-router-dom";
import {CHAT, FORGOT_PASSWORD, LOGIN, REGISTER} from "@/utils/routes.jsx";
import logo from "../assets/logo-esdm.png";
import VisibilityIcon from "@mui/icons-material/Visibility";
import VisibilityOffIcon from "@mui/icons-material/VisibilityOff";


export default function RegisterPage() {
    const [email, setEmail] = useState("");
    const [name, setName] = useState("");
    const [password, setPassword] = useState("");
    const { error, setError, register, loading } = useAuth();
    const navigate = useNavigate();
    const [showPassword, setShowPassword] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError("");

        if (!name || !email || !password) {
            setError("⚠️ Please enter both name, email, and password");
            return;
        }
        const result = await register(name, email, password);
        if (!result) {
            return;
        }
        navigate(LOGIN)
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
                                type="name"
                                placeholder="Enter Your Fullname"
                                fullWidth
                                margin="normal"
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                                sx={{
                                    bgcolor: "#ffffffff",            // background
                                    color: "#E1E6EB",             // text color
                                    borderRadius: 4,               // 6px approx
                                    "& .MuiOutlinedInput-notchedOutline": {
                                        borderColor: "#737373ff",     // border color
                                    },
                                    "&:hover .MuiOutlinedInput-notchedOutline": {
                                        borderColor: "#000000ff",     // hover border
                                    },
                                    "&.Mui-focused .MuiOutlinedInput-notchedOutline": {
                                        borderColor: "#000000ff",     // focused border
                                    },
                                    input: { color: "#3b3b3bff" },   // ensure text input color
                                }}
                            />
                        </FormControl>
                        <FormControl fullWidth margin="normal" variant="outlined">
                            <OutlinedInput
                                type="email"
                                placeholder="Enter Your Email"
                                fullWidth
                                margin="normal"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                sx={{
                                    bgcolor: "#ffffffff",
                                    borderRadius: 4,
                                    borderColor: "#777777ff",
                                    "& input": {
                                        backgroundColor: "#ffffffff",
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
                                        borderColor: "#000000ff",
                                    },
                                    "&.Mui-focused .MuiOutlinedInput-notchedOutline": {
                                        borderColor: "#000000ff",
                                    },
                                    input: { color: "#3b3b3bff" },
                                }}
                            />
                        </FormControl>

                        <FormControl fullWidth margin="normal" variant="outlined" >
                            <OutlinedInput
                                id="password"
                                placeholder="Enter Your Password"
                                type={showPassword ? "text" : "password"}
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                sx={{
                                    backgroundColor: "#ffffffff !important",
                                    borderRadius: 4,
                                    "& input": {
                                        backgroundColor: "#ffffffff",
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
                                        borderColor: "#000000ff",
                                    },
                                    "&.Mui-focused .MuiOutlinedInput-notchedOutline": {
                                        borderColor: "#000000ff",
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
                            {loading ? "Creating your account..." : "Register"}
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
                        Already have an account?
                    </Typography>

                    <Typography
                        variant="body1"
                        onClick={() => navigate(LOGIN)}
                        sx={{ fontWeight: "bold", color: "#000000", "&:hover": { cursor: "pointer", textDecoration: "underline" } }}
                    >
                        Login
                    </Typography>
                </Stack>
            </Grid>
        </Container>
    );
}
