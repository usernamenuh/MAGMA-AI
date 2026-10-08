import { keyframes } from "@mui/system";

export const bounce = keyframes`
  0%, 100% { transform: translateY(0); opacity: 0.5; }
  50% { transform: translateY(-7px); opacity: 1; }
`;

export const pulseGlow = keyframes`
  0%, 100% {
    transform: scale(1);
    box-shadow: 0 0 0 0 rgba(25, 118, 210, 0.2);
  }
  50% {
    transform: scale(1.04);
    box-shadow: 0 0 14px 4px rgba(25, 118, 210, 0.3);
  }
`;

export const shimmerGradient = keyframes`
  0% {
    background-position: -200% 0;
  }
  100% {
    background-position: 200% 0;
  }
`;
