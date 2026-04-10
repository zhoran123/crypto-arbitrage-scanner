import React, { useState, useEffect } from "react";
import { AnimatePresence, motion } from "framer-motion";
import Landing from "./Landing";
import Dashboard from "./Dashboard";
import Pricing from "./Pricing";

function getPage() {
  const h = window.location.hash.replace("#", "") || "/";
  if (h.startsWith("/dashboard")) return "dashboard";
  if (h.startsWith("/pricing")) return "pricing";
  return "landing";
}

const pageTransition = {
  initial: { opacity: 0, y: 14 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.25, 0.1, 0.25, 1] } },
  exit: { opacity: 0, y: -8, transition: { duration: 0.2, ease: [0.25, 0.1, 0.25, 1] } },
};

export default function App() {
  const [page, setPage] = useState(getPage);

  useEffect(() => {
    const fn = () => setPage(getPage());
    window.addEventListener("hashchange", fn);
    return () => window.removeEventListener("hashchange", fn);
  }, []);

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={page}
        variants={pageTransition}
        initial="initial"
        animate="animate"
        exit="exit"
        style={{ minHeight: "100vh" }}
      >
        {page === "dashboard" && <Dashboard />}
        {page === "pricing" && <Pricing />}
        {page === "landing" && <Landing />}
      </motion.div>
    </AnimatePresence>
  );
}
