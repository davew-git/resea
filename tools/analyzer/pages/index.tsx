import io from 'socket.io-client';
import { useState, useEffect, useRef } from 'react';
import LogStream from "../components/log_stream";
import TimeSeriesGraph from "../components/time_series_graph";
import { Grid, Container, Paper, makeStyles } from '@material-ui/core';
import classes from '*.module.css';

const useStyles = makeStyles((theme) => ({
    graphPaper: {
        height: 240,
    }
}));

export default function Home() {
    const classes = useStyles();
    const [tasks, setTasks] = useState([]);
    const [cpuLoadData, setCpuLoadData] = useState([]);
    const [kernelMemUsedData, setKernelMemUsedData] = useState([]);
    const [userMemUsedData, setUserMemUsedData] = useState([]);
    const [logItems, setLogEntries] = useState([]);
    const socket = useRef(null);

    useEffect(() => {
        socket.current = io("http://localhost:9091")
        return () => {
            socket.current.close();
        }
    }, []);

    useEffect(() => {
        socket.current.on("tasks", ({ tasks }) => {
            setTasks(tasks);
        });

        socket.current.on("log", e => {
            setLogEntries(prev => [...prev, e])
        });

        socket.current.on("sensor", e => {
            switch (e.key) {
                case "kernel.cpu_load":
                    setCpuLoadData(prev =>
                        [...prev.slice(-10), { x: e.timestamp, y: e.value }]
                    );
                break;
                case "kernel.mem_used":
                    setKernelMemUsedData(prev =>
                        [...prev.slice(-10), { x: e.timestamp, y: e.value }]
                    );
                break;
                case "bootstrap.mem_used":
                    setUserMemUsedData(prev =>
                        [...prev.slice(-10), { x: e.timestamp, y: e.value }]
                    );
                break;
            }
        });
    }, [socket]);

    return (
        <Container maxWidth="lg">
            <h1>foo</h1>
            <Grid container spacing={3}>
                <Grid item xs={12} md={8} lg={3}>
                    <Paper className={classes.graphPaper}>
                        <TimeSeriesGraph
                            data={[ { id: "cpu_load", data: cpuLoadData } ]}
                            yLegend="# of tasks in runqueue"
                            colorScheme="nivo"
                        />
                    </Paper>
                </Grid>
                <Grid item xs={12} md={4} lg={3}>
                    <Paper className={classes.graphPaper}>
                        <TimeSeriesGraph
                            data={[ { id: "mem_used", data: kernelMemUsedData } ]}
                            yLegend="MiB"
                            colorScheme="category10"
                        />
                    </Paper>
                </Grid>
                <Grid item xs={12} md={4} lg={3}>
                    <Paper className={classes.graphPaper}>
                        <TimeSeriesGraph
                            data={[ { id: "mem_used", data: userMemUsedData } ]}
                            yLegend="MiB"
                            colorScheme="category10"
                        />
                    </Paper>
                </Grid>
            </Grid>
        </Container>
    )

    return (
        <div>
            <div>
                <div>
                    <div style={{ height: "200px", display: "flex" }}>
                    </div>
                    <div title="Log" style={{ height: "300px" }}>
                        <div style={{ height: "200px" }}>
                            <LogStream items={logItems}></LogStream>
                        </div>
                    </div>
                </div>
                <div style={{ width: "350px", minHeight: "500px", marginLeft: "20px" }}>
                    <div title="Tasks" style={{ minHeight: "500px" }}>
                        <table>
                            <thead>
                                <tr>
                                    <th>Task ID</th>
                                    <th>Name</th>
                                    <th>State</th>
                                </tr>
                            </thead>
                            <tbody>
                                {tasks.map(task => (
                                    <tr key={task.id}>
                                        <td>{task.id}</td>
                                        <td>{task.name}</td>
                                        <td>
                                            {task.state}
                                            {task.state == "sending"
                                             && ` (to #${task.src_or_dst})`}
                                            {task.state == "receiving"
                                             && task.src
                                             && ` (from #${task.src_or_dst})`}
                                            {task.state == "receiving"
                                             && !task.src
                                             && ` (from any)`}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    )
}
