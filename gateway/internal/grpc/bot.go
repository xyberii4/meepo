package grpc

import (
	"context"
	"fmt"
	"io"

	"github.com/xyberii4/meepo/gateway/internal/grpc/pb"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
)

type BotService interface {
	JoinMeeting(ctx context.Context, meepoID, botID, url, name string) (<-chan *pb.JoinMeetingResponse, error)
	GetMeetingDetails(ctx context.Context, meepoID, botID string) (*pb.MeetingDetailsResponse, error)
	LeaveMeeting(ctx context.Context, meepoID, botID string) (*pb.LeaveMeetingResponse, error)
	Close() error
}

type botClient struct {
	conn   *grpc.ClientConn
	client pb.BotServiceClient
}

// NewBotClient now returns the BotService interface for better abstraction.
func NewBotClient(addr string) (BotService, error) {
	conn, err := grpc.NewClient(
		addr,
		grpc.WithTransportCredentials(insecure.NewCredentials()),
	)
	if err != nil {
		return nil, err
	}

	client := &botClient{
		conn:   conn,
		client: pb.NewBotServiceClient(conn),
	}

	return client, nil
}

// JoinMeeting initiates a streaming RPC to join a meeting.
// returns a channel that receives responses from the server.
func (c *botClient) JoinMeeting(ctx context.Context, meepoID, botID, url, name string) (<-chan *pb.JoinMeetingResponse, error) {
	stream, err := c.client.JoinMeeting(ctx,
		&pb.JoinMeetingRequest{
			MeepoId: meepoID,
			BotId:   botID,
			Url:     url,
			Name:    name,
		},
	)
	if err != nil {
		return nil, err
	}

	responses := make(chan *pb.JoinMeetingResponse)

	go func() {
		defer close(responses)

		for {
			resp, err := stream.Recv()

			if err == io.EOF {
				// Stream closed
				return
			}

			if err != nil {
				fmt.Println("Error receiving from JoinMeeting stream:", err)
				return
			}

			// send response to the channel
			// will block if the receiver isn't ready
			select {
			case responses <- resp:
				// response sent
			case <-ctx.Done():
				// cancelled context
				return
			}
		}
	}()

	return responses, nil
}

func (c *botClient) GetMeetingDetails(ctx context.Context, meepoID, botID string) (*pb.MeetingDetailsResponse, error) {
	return c.client.GetMeetingDetails(ctx, &pb.MeetingDetailsRequest{
		MeepoId: meepoID,
		BotId:   botID,
	})
}

func (c *botClient) LeaveMeeting(ctx context.Context, meepoID, botID string) (*pb.LeaveMeetingResponse, error) {
	return c.client.LeaveMeeting(ctx, &pb.LeaveMeetingRequest{
		MeepoId: meepoID,
		BotId:   botID,
	})
}

func (c *botClient) Close() error {
	return c.conn.Close()
}
