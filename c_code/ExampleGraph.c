// Assume those files, functions, and types exist
#include "ExampleGraph.h"
#include "Configuration.h"
#include "DataflowGraph.h"
#include "Utility.h"

static Graph CreateTaskDependencyGraph(int arg1, int arg2, int arg3)
{
    Node *start = Utility_CreateStart();
    Node *task1 = Utility_CreateTask(arg1);
    Node *task2 = Utility_CreateTask(arg2);
    Node *task3 = Utility_CreateTask(arg3);
    Node *end = Utility_CreateEnd();

    // Task 2, 3 definitely wait for task 1
    Utility_LinkDirectedHard(start, task1);
    Utility_LinkDirectedHard(task1, task2);
    Utility_LinkDirectedHard(task1, task3);
    // End waits for either task 2 or task3
    Utility_LinkDirectedSoft(task2, end);
    Utility_LinkDirectedSoft(task3, end);

    Graph taskDependencyGraph = {.start = start, .end = end};
    return taskDependencyGraph;
}

static Graph CreateFinishingGraph(bool condition1)
{
    Node *start = Utility_CreateStart();
    Node *end = Utility_CreateEnd();

    bool condition2 = Configuration_GetCondition2();
    bool condition4 = Configuration_GetCondition4();
    bool condition7 = Configuration_GetCondition7();

    if (condition1 && condition2)
    {
        Node *task3 = Utility_CreateTask(Configuration_GetTask3Arg());
        Node *task6 = Utility_CreateTask(Configuration_GetTask6Arg());

        Utility_LinkDirectedHard(start, task3);
        Utility_LinkDirectedHard(task3, task6);
        Utility_LinkDirectedHard(task3, end);
    }
    else if (condition1)
    {
        Node *task1 = Utility_CreateTask(Configuration_GetTask1Arg());
        Utility_LinkDirectedHard(start, task1);

        if (condition4)
        {
            Node *task4 = Utility_CreateTask(Configuration_GetTask4Arg());
            Utility_LinkDirectedHard(task1, task4);
            Utility_LinkDirectedHard(task4, end);
        }

        Utility_LinkDirectedHard(task1, end);
    }
    else
    {
        Node *task2 = Utility_CreateTask(Configuration_GetTask2Arg());
        Node *task5 = Utility_CreateTask(Configuration_GetTask5Arg());

        Utility_LinkDirectedHard(start, task2);
        Utility_LinkDirectedHard(start, task5);
        Utility_LinkDirectedSoft(task2, end);
        Utility_LinkDirectedSoft(task2, end);
    }

    if (!condition7)
    {
        Node *task7 = Utility_CreateTask(Configuration_GetTask7Arg());
        Utility_LinkDirectedHard(start, task7);
        Utility_LinkDirectedSoft(task7, end);
    }

    Graph finishingGraph = {.start = start, .end = end};
    return finishingGraph;
}

Graph ExampleGraph_Create(void)
{
    Graph taskDependencyGraph1 = CreateTaskDependencyGraph(1, 2, 3);
    Graph taskDependencyGraph2 = CreateTaskDependencyGraph(4, 5, 6);
    Graph dataflowGraph1 = DataflowGraph_Create();
    Graph dataflowGraph2 = DataflowGraph_Create();
    Graph finishingGraph = CreateFinishingGraph(true);

    // Undirected, just because I can
    Utility_LinkUndirected(dataflowGraph1.end, taskDependencyGraph1.start);
    Utility_LinkUndirected(dataflowGraph1.end, taskDependencyGraph2.start);
    // If graph2 finishes first, dataflow can execute.
    // If graph1 finishes first, dataflow still waits for graph2
    Utility_LinkDirectedSoft(taskDependencyGraph1.end, dataflowGraph2.start); // graph1 triggers dataflow
    Utility_LinkDirectedHard(taskDependencyGraph2.end, dataflowGraph2.start); // but dataflow definitely waits for graph2

    Utility_LinkDirectedHard(dataflowGraph2.end, finishingGraph.start);

    Graph exampleGraph = {.start = dataflowGraph.start, .end = finishingGraph.end};
    return exampleGraph;
}
